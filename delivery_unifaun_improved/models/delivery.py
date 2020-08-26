# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp.tools import safe_eval
import openerp.addons.decimal_precision as dp
import requests
from requests.auth import HTTPBasicAuth
import json
import base64
from urllib import urlencode
import traceback
from math import ceil
from pprint import PrettyPrinter

import logging
_logger = logging.getLogger(__name__)

# Unifaunobjekt knutna till picking_id
#stock.picking.unifaun.status
#stock.picking.unifaun.param
#stock.picking.unifaun.pdf

READ_ONLY_STATES = {'done': [('readonly', True)], 'sent': [('readonly', True)], 'cancel': [('readonly', True)]}

class UnifaunPackage(models.Model):
    _name = 'unifaun.package'
    _description = 'Unifaun Package'

    def _default_contents(self):
        return _(self.env['ir.config_parameter'].get_param('unifaun.parcel_description', 'Goods'))

    state = fields.Selection(related='unifaun_id.state')
    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order', required=True, ondelete='cascade', states=READ_ONLY_STATES)
    ul_id = fields.Many2one(comodel_name='product.ul', string='Logistical Unit', states=READ_ONLY_STATES)
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging', help="This field should be completed only if everything inside the package share the same product, otherwise it doesn't really make sense.", states=READ_ONLY_STATES)
    shipper_package_code = fields.Char(string='Package Code', help="The shipping company's code for this packaging type.", states=READ_ONLY_STATES)
    line_ids = fields.One2many(comodel_name='unifaun.package.line', inverse_name='package_id', string='Products')
    name = fields.Char(string='Reference', states=READ_ONLY_STATES)
    contents = fields.Char(string='Contents', default=_default_contents, states=READ_ONLY_STATES)
    copies = fields.Integer(string='Copies', default=1, states=READ_ONLY_STATES)
    weight = fields.Float(string='Weight', compute='_calculate_weight', store=True, digits_compute=dp.get_precision('Stock Weight'))
    weight_calc = fields.Float(string='Weight', compute='_calculate_weight', store=True, digits_compute=dp.get_precision('Stock Weight'))
    weight_spec = fields.Float(string='Specified Weight', digits_compute=dp.get_precision('Stock Weight'), help="Use this field to override the calculated weight.", states=READ_ONLY_STATES)

    @api.multi
    @api.depends('line_ids.product_id', 'line_ids.uom_id',
                 'line_ids.qty', 'weight_spec')
    def _calculate_weight(self):
        """Calculate the weight of the packages. Includes boxes/pallets etc."""
        uom_obj = self.env['product.uom']
        for package in self:
            # TODO: Does this check work or will it be set to 0 if state != draft?
            _logger.warn(self.unifaun_id.state)
            if package.unifaun_id.state == 'draft':
                weight = 0.00
                for line in package.line_ids:
                    weight += line.product_qty * line.product_id.weight
                # Box / Pallet
                if package.ul_id:
                    weight += package.ul_id.weight
                # Product distribution packages, e.g. boxes stapled on a pallet.
                if package.packaging_id:
                    weight += ceil(package.product_qty / package.packaging_id.qty) * package.packaging_id.ul.weight
                package.weight_calc = weight
                if package.weight_spec:
                    package.weight = package.weight_spec
                else:
                    package.weight = weight

    @api.one
    def get_parcel_values(self):
        """Return a dict of parcel data to be used in a Unifaun shipment record."""
        vals = {
            'copies': self.copies,
            'weight': self.weight,
            'contents': self.contents,
            'valuePerParcel': False,
        }
        if self.name:
            vals['reference'] = self.name # ??? Not saved in shipment
        if self.ul_id:
            package_code = self.ul_id.get_unifaun_package_code(self.carrier_id)
            if package_code:
                vals['packageCode'] = package_code
            #TODO: Add default package_code
        # TODO: Add volume, length, width, height
        return vals

class UnifaunPackageLine(models.Model):
    _name = 'unifaun.package.line'
    _description = 'Unifaun Order Line'

    state = fields.Selection(related='unifaun_id.state')
    package_id = fields.Many2one(comodel_name='unifaun.package', string='Package', required=True, ondelete='cascade', states=READ_ONLY_STATES)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True, states=READ_ONLY_STATES)
    name = fields.Char(related='product_id.display_name')
    uom_id = fields.Many2one(comodel_name='product.uom', string='Unit of Measure', required=True, states=READ_ONLY_STATES)
    qty = fields.Float(string='Quantity', states=READ_ONLY_STATES)
    product_qty = fields.Float(string='Quantity', compute='_calculate_product_qty')
    unifaun_id = fields.Many2one(related='package_id.unifaun_id')

    @api.multi
    @api.depends('product_id', 'uom_id', 'qty')
    def _calculate_product_qty(self):
        uom_obj = self.env['product.uom']
        for line in self:
            # TODO: Does this check work or will it be set to 0 if state != draft?
            if line.unifaun_id.state == 'draft':
                line.product_qty = uom_obj._compute_qty_obj(line.uom_id, line.qty, line.product_id.uom_id)

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    sender_contact_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact Person',
        )

class UnifaunOrder(models.Model):
    _name = 'unifaun.order'
    _inherit = ['mail.thread']
    _description = 'Unifaun Order'

    state = fields.Selection(
        string='State',
        selection=[
            ('group', 'Group'),
            ('draft', 'Draft'),
            ('sent', 'Sent'),
            ('done', 'Confirmed'),
            ('cancel', 'Cancelled'),
            ('error', 'Error')],
        default='draft',
        required=True,
        help="""*[group]: Waiting for pickings to be completed.""")
    name = fields.Char(
        string='Reference',
        select=True,
        states=READ_ONLY_STATES,
        copy=False)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Recipient',
        states=READ_ONLY_STATES,
        required=True)
    sender_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Sender',
        states=READ_ONLY_STATES,
        required=True)
    sender_contact_id = fields.Many2one(
        comodel_name='res.partner',
        string='Sender Contact',
        states=READ_ONLY_STATES,
        )
    contact_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Recipient Contact',
        states=READ_ONLY_STATES)
    picking_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='unifaun_id',
        string='Picking Orders')
    shipmentid = fields.Char(string='Unifaun Shipment ID', copy=False)
    stored_shipmentid = fields.Char(string='Unifaun Stored Shipment ID', copy=False)
    pdf_ids = fields.One2many(
        string='Unifaun PDFs',
        comodel_name='stock.picking.unifaun.pdf',
        inverse_name='unifaun_id',
        copy=False)
    status_ids = fields.One2many(
        comodel_name='stock.picking.unifaun.status',
        inverse_name='unifaun_id',
        string='Unifaun Status',
        copy=False)
    param_ids = fields.One2many(
        string='Parameters',
        comodel_name='stock.picking.unifaun.param',
        inverse_name='unifaun_id')
    weight = fields.Float(
        string='Weight',
        digits_compute=dp.get_precision('Stock Weight'),
        compute='_calculate_weight',
        store=True)
    carrier_id = fields.Many2one(comodel_name='delivery.carrier', string='Carrier', required=True)
    carrier_tracking_ref = fields.Char(string='Carrier Tracking Ref', copy=False)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        select=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.picking'))
    date = fields.Datetime(
        string='Date',
        help="The planned date of the delivery",
        select=True,
        states=READ_ONLY_STATES,
        track_visibility='onchange')
    package_ids = fields.One2many(comodel_name='unifaun.package', inverse_name='unifaun_id', string='Packages')
    line_ids = fields.One2many(related='package_ids.line_ids', string='Package Contents')

    @api.one
    @api.depends(
        'package_ids.line_ids.qty',
        'package_ids.line_ids.uom_id',
        'package_ids.line_ids.product_id',
        'package_ids.weight_spec',
    )
    def _calculate_weight(self):
        if self.state == 'draft':
            weight = 0.00
            for package in self.package_ids:
                weight += package.weight
            self.weight = weight
    
    # https://www.unifaunonline.se/rs-docs/
    # Create shipment to be completed manually
    # catch carrier_tracking_ref (to be mailed? add on waybill)
    
    # ~ @api.one
    # ~ @api.depends('picking_ids.pack_operation_ids.result_package_id')
    # ~ def _compute_package_ids(self):
        # ~ if self.state == 'draft':
            # ~ self.package_ids = self.picking_ids.mapped('pack_operation_ids').mapped('result_package_id')
        
    @api.onchange('carrier_id')
    def onchange_carrier(self):
        self.param_ids = None
        if self.carrier_id.is_unifaun and self.carrier_id.unifaun_param_ids:
            self.param_ids = [(0, 0, d) for d in self.carrier_id.unifaun_param_ids.get_picking_param_values()]
            self.param_ids.compute_default_value()
    
    @api.multi
    def get_unifaun_language(self):
        translate = {
            'en_US': 'gb',
            'sv_SE': 'se',
            'no_NO': 'no',
            'nn_NO': 'no',
            'nb_NO': 'no',
            'fi_FI': 'fi',
            'da_DK': 'dk'
        }
        
        return translate.get(self.partner_id.lang, 'gb') 
    
    @api.model
    def create_from_pickings(self, pickings):
        """Create a Unifaun Order from one or more Picking Orders."""
        problems = self.check_picking_compatibility(pickings)
        if problems:
            raise Warning(_("Could not make a Unifaun order from %s.\n%s") % (
                ', '.join([p.name for p in pickings]),
                '\n'.join(problems)))
        order = None
        for picking in pickings:
            if picking.unifaun_id:
                if order and order != picking.unifaun_id:
                    raise Warning(_("Found multiple Unifaun orders already on the pickings!"))
                order = picking.unifaun_id
        if order and order.state not in ('group', 'draft'):
            raise Warning(_("Found a Unifaun orders already on the pickings. State is not Draft!"))
        values = self.get_order_vals_from_pickings(pickings)
        _logger.warn(values)
        if order:
            order.write(values)
        else:
            order = self.create(values)
        pickings.write({'unifaun_id': order.id})
        order.onchange_carrier()
        return order

    @api.model
    def check_picking_compatibility(self, pickings):
        """Check if the pickings can be sent as the same Unifaun Order."""
        problems = []
        field_data = self.get_picking_compatibility_data(pickings)
        # Check required fields
        for field in field_data['required']:
            for picking in pickings:
                if not getattr(picking, field):
                    problems.append(_("%s is missing value for required field %s.") % (picking.name, field))
        # Check that certain fields are identical
        if len(pickings) > 1:
            for field in field_data['identical']:
                values = [getattr(p, field) for p in pickings]
                if not all([v == values[0] for v in values]):
                    problems.append(_("Differing values for %s.") % field)
        return problems
    
    @api.model
    def get_picking_compatibility_data(self, pickings):
        result = {
            'required': [
                'carrier_id',
                'is_unifaun',
                ],
            'identical': [
                'carrier_id',
                'partner_id',
                # ~ 'picking_type_id',
                ],
            }
        # Lazy handling of sale_id to avoid an extra unifaun_sale module
        if hasattr(pickings, 'sale_id'):
            result['identical'] = 'sale_id'
        return result

    @api.model
    def get_order_vals_from_pickings(self, pickings):
        picking = pickings[0]
        # Choose sender and receiver based on picking type (in or out).
        if picking.picking_type_id.code == 'incoming':
            receiver = picking.picking_type_id.warehouse_id.partner_id
            sender = picking.partner_id
        elif picking.picking_type_id.code == 'outgoing':
            sender = picking.picking_type_id.warehouse_id.partner_id
            receiver = picking.partner_id
        receiver_contact = self.get_contact_from_pickings(picking, receiver)
        sender_contact = picking.picking_type_id.warehouse_id.sender_contact_id
        # TODO: Make name a sequence of its own?
        values = {
            'name': picking.name,
            'state': 'draft',
            'partner_id': receiver.id,
            'contact_partner_id': receiver_contact and receiver_contact.id or None,
            'sender_partner_id': sender.id,
            'sender_contact_id': sender_contact and sender_contact.id or None,
            'carrier_id': picking.carrier_id.id,
            'company_id': picking.company_id.id,
            'date': max([p.date_done for p in pickings]),
            'package_ids': self.get_package_values_from_pickings(pickings),
        }
        return values

    @api.model
    def get_contact_from_pickings(self, pickings, partner_id):
        """Return the receiving partner contact."""
        if hasattr(pickings, 'sale_id'):
            for picking in pickings:
                if picking.sale_id:
                    return picking.sale_id.partner_id
                    
    # ~ @api.model
    # ~ def get_sender_contact_from_pickings(self, pickings, parnter_id):
        # ~ """Return the receiving partner contact."""
        # ~ if hasattr(pickings, 'sale_id'):
            # ~ for picking in pickings:
                # ~ if picking.sale_id:
                    # ~ return picking.sale_id.partner_id
        
        
        

    @api.model
    def get_package_values_from_pickings(self, pickings):
        packages = []
        pickings_spec = pickings.filtered(lambda p: p.unifaun_parcel_weight and p.unifaun_parcel_count)
        if pickings_spec:
            # Package weight and count has been specified on pickings
            lines = []
            # Handle lines on pickings not specified
            for op in (pickings - pickings_spec).mapped('pack_operation_ids'):
                values = op.unifaun_package_line_values()
                if values:
                    lines.append((0, 0, values))
            for picking in pickings_spec:
                for op in picking.pack_operation_ids:
                    values = op.unifaun_package_line_values()
                    if values:
                        lines.append((0, 0, values))
                packages.append((0, 0, {
                    'name': 'Package %s' % picking.name,
                    'copies': picking.unifaun_parcel_count,
                    'weight_spec': picking.unifaun_parcel_weight,
                    'line_ids': lines,
                }))
                lines = []
            return packages
        # TODO: Everything below needs to tested and probably reworked
        ### Handle packages from the pickings ###
        for package in pickings.mapped('package_ids'):
            values = package.unifaun_package_values()
            for op in pickings.mapped('pack_operation_ids').filtered(lambda op: op.package_id == package_id):
                values['line_ids'].append((0, 0, op.unifaun_package_line_values()))
            packages.append((0, 0, values))
        ### Check for packops not in packages ###
        pack_ops = []
        # Handle pickings that should all be their own package
        for picking in pickings.filtered('unifaun_own_package'):
            ops = picking.pack_operation_ids.filtered(lambda o: not o.result_package_id)
            if ops:
                pack_ops.append(ops)
        # Handle pickings that are in the same package
        ops = pickings.filtered(
            lambda p: not p.unifaun_own_package).mapped(
                'pack_operation_ids').filtered(lambda o: not o.result_package_id)
        if ops:
            pack_ops.append(ops)
        # Create packages from the non-packaged packops
        p_count = 1
        for package_ops in pack_ops:
            lines = []
            for op in package_ops:
                values = op.unifaun_package_line_values()
                if values:
                    lines.append((0, 0, values))
            if lines:
                weight = package_ops.mapped('picking_id').mapped('unifaun_parcel_weight')
                weight = weight and max(weight) or 0
                packages.append((0, 0, {
                    # ~ 'ul_id': None,
                    # ~ 'packaging_id': None,
                    # ~ 'shipper_package_code': None,
                    'name': 'Package %s' % p_count,
                    # ~ 'contents': '',
                    'weight_spec': weight,
                    'line_ids': lines,
                }))
                p_count += 1
        return packages
            

    @api.multi
    def get_unifaun_sender_reference(self):
        return self.name 

    @api.one
    def set_unifaun_status(self, statuses):
        if self.status_ids:
            self.status_ids.unlink()
        for d in statuses:
            self.env['stock.picking.unifaun.status'].create({
                'field': d.get('field'),
                'name': d.get('message'),
                'type': d.get('type'),
                'location': d.get('location'),
                'message_code': d.get('messageCode'),
                'raw_data': u'%s' %d,
                'unifaun_id': self.id,
            })
        # ~ {u'field': u'Party_CustNo', u'message': u'invalid check digit', u'type': u'error', u'location': u'', u'messageCode': u'Checkdigit'}

    @api.multi
    def unifaun_track_and_trace_url(self):
        """Return an URL for Unifaun Track & Trace."""
        # https://www.unifaunonline.se/ufoweb-prod-201812111106/public/SUP/UO/UO-101-TrackandTrace-en.pdf
        # TODO: Add support for regions (what does regions even do?)
        if self.shipmentid:
            parameters = {
                'apiKey': self.env['ir.config_parameter'].get_param('unifaun.api_key'),
                'reference': self.get_unifaun_sender_reference(),
                'templateId': self.env['ir.config_parameter'].get_param('unifaun.templateid')}
            
            region = 'se'
            lang = self.get_unifaun_language()
            
            res = 'https://www.unifaunonline.com/ext.uo.%s.%s.track?&%s' % (region, lang, urlencode(parameters).replace('&amp;', '&'))
        else:
            res = ''
        return res


    @api.multi
    def unifaun_get_parcel_data(self):
        """Return a list of parcel dicts to send in unifaun shipment records."""
        # valuePerParcel (boolean)
        #     true defines information for each parcel individually.
        #     false defines information for an entire row of parcels.
        # copies (integer, minimum 1)
        #     Number of parcels.
        # marking (string)
        #     Goods marking.
        # packageCode (string)
        #     Package code. Refer to Help -> Code lists in your account for available package types.
        # packageText (string)
        #     Package text. Used for certain services.
        # weight (number, minimum 0)
        #     Weight.
        # volume (number, minimum 0)
        #     Volume.
        # length (number, minimum 0)
        #     Length.
        # width (number, minimum 0)
        #     Width.
        # height (number, minimum 0)
        #     Height.
        # loadingMeters (number, minimum 0)
        #     Load meters.
        # itemNo (string)
        #     Item number. Used for certain services.
        # contents (string)
        #     Contents.
        # reference (string)
        #     Parcel reference. Used for certain services.
        # parcelNos (array of string)
        #     Parcel numbers. The array should have copies number of parcel numbers. Note: A special license key is required to use this value.
        # stackable (boolean)
        #     Parcel can be stacked. Used for certain services.
        return self.package_ids.get_parcel_values()
    
    @api.multi
    def unifaun_sender_record(self, sender):
        sender_contact = None
        if sender.parent_id and sender.type == 'contact':
            sender_contact = sender
            sender = self.env['res.partner'].browse(sender.parent_id.address_get(['delivery'])['delivery'])
        rec = {
                'name': sender.name,
                'address1': sender.street or '',
                'address2': sender.street2 or '',
                'zipcode': sender.zip or '',
                'city': sender.city or '',
                'state': sender.state_id and sender.state_id.name or '',
                'country': sender.country_id and sender.country_id.code or '',
                'phone': sender.phone or sender.mobile or '',
                'mobile': sender.mobile or '',
                'email': sender.email or '',
            }
        if sender_contact:
            rec.update({
                'phone': sender_contact.phone or sender_contact.mobile or '',
                'mobile': sender_contact.mobile or '',
                'email': sender_contact.email or '',
                'contact': sender_contact.name,
            })
        return rec
    
    @api.multi
    def unifaun_receiver_contact(self, receiver, current_values):
        """Contact info for the receiver record. Default is just to add the contact name, but could change phone number, email etc."""
        contact_data = {}
        if self.contact_partner_id:
            contact_data['contact'] = self.contact_partner_id.name
        return contact_data
        
    @api.multi
    def unifaun_sender_contact(self, sender, current_values):
        """Contact info for the receiver record. Default is just to add the contact name, but could change phone number, email etc."""
        contact_data = {}
        if self.sender_contact_id:
            contact_data['contact'] = self.sender_contact_id.name
        return contact_data
    
    @api.multi
    def unifaun_receiver_record(self, receiver):
        rec = {
                'name': receiver.name,
                'address1': receiver.street or '',
                'address2': receiver.street2 or '',
                'zipcode': receiver.zip or '',
                'city': receiver.city or '',
                'state': receiver.state_id and receiver.state_id.name or '',
                'country': receiver.country_id and receiver.country_id.code or '',
                'phone': receiver.phone or receiver.mobile or '',
                'mobile': receiver.mobile or '',
                'email': receiver.email or '',
            }
        name_method = self.env['ir.config_parameter'].get_param('unifaun.receiver_name_method', 'default')
        if name_method == 'parent' and receiver.parent_id:
            rec['name'] = receiver.parent_id.name
        elif name_method == 'commercial':
            rec['name'] = receiver.commercial_partner_id.name
        return rec
    
    @api.one
    def order_stored_shipment(self):
        """Create a stored shipment."""
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        if self.shipmentid:
            raise Warning(_('The stored shipment has already been confirmed (there is a Shipment id).'))
        if self.stored_shipmentid:
            self.delete_stored_shipment()
        receiver_record = self.unifaun_receiver_record(self.partner_id)
        receiver_record.update(self.unifaun_receiver_contact(self.partner_id, receiver_record))
        sender_record = self.unifaun_sender_record(self.sender_partner_id)
        sender_record.update(self.unifaun_sender_contact(self.sender_partner_id, sender_record))
        rec = {
            'sender': sender_record,
            'senderPartners': [{
                'id': self.carrier_id.unifaun_sender or '',
                'custNo': self.carrier_id.unifaun_customer_no or '',
            }],
            'receiver': receiver_record,
            'service': {
                'id': self.carrier_id.unifaun_service_code or '',
            },
            'parcels': self.package_ids.get_parcel_values(),
            'orderNo': self.name,
            'senderReference': self.get_unifaun_sender_reference(),
            #~ "receiverReference": "receiver ref 345",
            #~ "options": [{
                #~ "message": "This is order number 123",
                #~ "to": "sales@unifaun.com",
                #~ "id": "ENOT",
                #~ "languageCode": "SE",
                #~ "from": "info@unifaun.com"
            #~ }],
        }
        
        if self.param_ids:
            self.param_ids.add_to_record(rec)

        response = self.carrier_id.unifaun_send('stored-shipments', None, rec)
        printer = PrettyPrinter()
        if type(response) == dict:
            _logger.warn('\n%s\n' % response)
            self.stored_shipmentid = response.get('id', '')

            self.env['mail.message'].create({
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s<br/>" % (printer.pformat(rec), printer.pformat(response))),
                # ~ 'body': _(u"Unifaun<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
            self.set_unifaun_status(response.get('statuses') or [])
            if response.get('status') == 'READY':
                self.state = 'sent'
            # ~ elif response.get('status') == 'INVALID':
            else:
                self.state = 'error'
        else:
            self.env['mail.message'].create({
                # ~ 'body': _("Unifaun error!<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s<br/>" % (printer.pformat(rec), printer.pformat(response))),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.info('Unifaun Order Transport: rec %s response %s' % (rec, response))

    @api.one
    def delete_stored_shipment(self):
        if not self.stored_shipmentid:
            raise Warning(_('No stored shipment found for this order.'))
        if self.shipmentid:
            raise Warning(_('The stored shipment has already been confirmed (there is a Shipment id).'))
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        res, response = self.carrier_id.unifaun_delete('/stored-shipments/%s' % self.stored_shipmentid)
        if res:
            self.stored_shipmentid = None
            self.state = 'draft'
        else:
            message = _('Failed to delete stored shipment %s!' % self.stored_shipmentid)
            if response.status_code == 404:
                message += _('\n\n404: Stored shipment not found')
            else:
                message += _('\n\n%s: %s') % (response.status_code, response.text)
            raise Warning(message)

    @api.one
    def confirm_stored_shipment(self):
        """Create shipment(s) from a stored shipment."""
        if not self.stored_shipmentid:
            raise Warning(_('No stored shipment found for this order.'))
        if self.shipmentid:
            raise Warning(_('The stored shipment has already been confirmed (there is a Shipment id).'))
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        if not self.carrier_id.unifaun_print_settings_id:
            raise Warning(_("No print settings found for carrier %s") % self.carrier_id.name)
        rec = {}
        # Send label printing instructions
        for i in range(1, 5):
            format = getattr(self.carrier_id.unifaun_print_settings_id, 'format_%s' % i)
            if format == 'null':
                rec.update({
                    'target%sMedia' % i: None,
                    'target%sXOffset' % i: 0.0,
                    'target%sYOffset' % i: 0.0,
                })
            else:
                x_offset = getattr(self.carrier_id.unifaun_print_settings_id, 'x_offset_%s' % i)
                y_offset = getattr(self.carrier_id.unifaun_print_settings_id, 'y_offset_%s' % i)
                rec.update({
                    'target%sMedia' % i: format,
                    'target%sXOffset' % i: x_offset,
                    'target%sYOffset' % i: y_offset,
                })
        printer = PrettyPrinter()
        response = self.carrier_id.unifaun_send('stored-shipments/%s/shipments' % self.stored_shipmentid, None, rec)
        if type(response) == list:
            _logger.warn('\n%s\n' % response)
            unifaun_shipmentid = []
            carrier_tracking_ref = []
            unifaun_pdfs = []
            for r in response:
                # Could be more than one shipment.
                if r.get('shipmentNo'):
                    carrier_tracking_ref.append(r.get('shipmentNo'))
                if r.get('id'):
                    unifaun_shipmentid.append(r.get('id'))
                if r.get('pdfs'):
                    unifaun_pdfs += r['pdfs']
            self.carrier_tracking_ref = ', '.join(carrier_tracking_ref)
            self.shipmentid = ', '.join(unifaun_shipmentid)
            # create an attachment
            # TODO: several pdfs?
            _logger.warn(unifaun_pdfs)
            for pdf in unifaun_pdfs:
                attachment = self.carrier_id.unifaun_download(pdf)
                attachment.write({
                    'res_model': self._name,
                    'res_id': self.id
                })
                self.env['stock.picking.unifaun.pdf'].create({
                    'name': pdf.get('description'),
                    'href': pdf.get('href'),
                    'unifaunid': pdf.get('id'),
                    'attachment_id': attachment.id,
                    'unifaun_id': self.id,
                })
            
            self.env['mail.message'].create({
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s" % (printer.pformat(rec), printer.pformat(response))),
                'subject': "Shipment(s) Created",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
            self.unifaun_send_track_mail_silent()
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s" % (printer.pformat(rec), printer.pformat(response))),
                'subject': "Create Shipment",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.info('Unifaun Order Transport: rec %s response %s' % (rec,response))

    @api.multi
    def unifaun_send_track_mail(self):
        self.ensure_one()
        template_id = self.env.ref('delivery_unifaun_base.unifaun_order_email_template').id
        try:
            compose_form_id = self.env['ir.model.data'].get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'unifaun.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_partner_ids': [(6, 0, [self[0].partner_id.id])],
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
        
    @api.one
    def unifaun_send_track_mail_silent(self):
        if self.env.context.get('unifaun_track_force_send') or self.env['ir.config_parameter'].get_param('unifaun.sendemail', '1') == '1':
            template = self.env.ref('delivery_unifaun_base.unifaun_email_template')
            try:
                template.send_mail(self.id)
            except:
                self.env['mail.message'].create({
                    'body': _("Mail error!<br/>Could not send email<br/>%s" % traceback.format_exc().replace('\n', '<br/>')),
                    'subject': "Send tracking mail",
                    'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                    'res_id': self.id,
                    'model': self._name,
                    'type': 'notification',
                })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
