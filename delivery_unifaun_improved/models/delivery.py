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

class stock_picking_unifaun_status(models.Model):
    _inherit = 'stock.picking.unifaun.status'

    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order')
    # unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order', inverse_name='unifaun_id')
    picking_id = fields.Many2one(required=False, ondelete=None)

class StockPickingUnifaunParam(models.Model):
    _inherit = 'stock.picking.unifaun.param'

    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order')
    # unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order', inverse_name='unifaun_id')
    picking_id = fields.Many2one(required=False, ondelete=None)

class StockPickingUnifuanPdf(models.Model):
    _inherit = 'stock.picking.unifaun.pdf'

    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order')
    # unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order', inverse_name='unifaun_id')
    picking_id = fields.Many2one(required=False, ondelete=None)

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order')

class UnifaunPackage(models.Model):
    _name = 'unifaun.package'
    _description = 'Unifaun Package'

    def _default_contents(self):
        return _(self.env['ir.config_parameter'].get_param('unifaun.parcel_description', 'Goods'))
    
    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order', required=True, ondelete='cascade')
    ul_id = fields.Many2one(comodel_name='stock.quant.package', string='Logistical Unit')
    packaging_id = fields.Many2one(comodel_name='stock.quant.package', string='Packaging', help="This field should be completed only if everything inside the package share the same product, otherwise it doesn't really make sense.")
    shipper_package_code = fields.Char(string='Package Code', help="The shipping company's code for this packaging type.")
    line_ids = fields.One2many(comodel_name='unifaun.package', inverse_name='package_id', string='Contents')
    name = fields.Char(string='Reference')
    contents = fields.Char(string='Contents', default=_default_contents)
    weight = fields.Float(string='Weight', compute='_calculate_weight', store=True, digits_compute=dp.get_precision('Stock Weight'))
    spec_weight = fields.Float(string='Specified Weight', digits_compute=dp.get_precision('Stock Weight'), help="Use this field to override the calculated weight.")
    
    @api.multi
    @api.depends('line_ids.product_id', 'line_ids.product_uom_id',
                 'line_ids.qty')
    def _calculate_weight(self):
        """Calculate the weight of the packages. Includes boxes/pallets etc."""
        uom_obj = env['product.uom']
        for package in self:
            # TODO: Does this check work or will it be set to 0 if state != draft?
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
                package.weight = weight

    @api.one
    def get_parcel_values(self):
        """Return a dict of parcel data to be used in a Unifaun shipment record."""
        vals = {
            'copies': 1,
            'weight': self.shipping_weight or self.weight or 0,
            'contents': self.contents,
            'valuePerParcel': True,
        }
        if self.name:
            vals['reference'] = self.name, # ??? Not saved in shipment
        if self.ul_id:
            package_code = self.ul_id.get_unifaun_package_code(self.carrier_id)
            if package_code:
                vals['packageCode'] = package_code
            # TODO: Add volume, length, width, height
        return vals

class UnifaunPackageLine(models.Model):
    _name = 'unifaun.package.line'
    _description = 'Unifaun Order Line'

    package_id = fields.Many2one(comodel_name='unifaun.package', string='Package', required=True, ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    uom_id = fields.Many2one(comodel_name='product.uom', string='Unit of Measure', required=True)
    qty = fields.Float(string='Quantity')
    product_qty = fields.Float(string='Quantity', compute='_calculate_product_qty')
    unifaun_id = fields.Many2one(related='package_id.unifaun_id')

    @api.multi
    @api.depends('product_id', 'uom_id', 'qty')
    def _calculate_product_qty(self):
        uom_obj = env['product.uom']
        for line in self:
            # TODO: Does this check work or will it be set to 0 if state != draft?
            if line.unifaun_id.state == 'draft':
                line.product_qty = uom_obj._compute_qty_obj(line.uom_id, line.qty, line.product_id.uom_id)

class UnifaunOrder(models.Model):
    _name = 'unifaun.order'
    _description = 'Unifaun Order'

    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    picking_ids = fields.One2many(comodel_name='stock.picking', inverse_name='unifaun_id', string='Picking Orders')
    shipmentid = fields.Char(string='Unifaun Shipment ID', copy=False)
    stored_shipmentid = fields.Char(string='Unifaun Stored Shipment ID', copy=False)
    pdf_ids = fields.One2many(string='Unifaun PDFs', comodel_name='stock.picking.unifaun.pdf', inverse_name='unifaun_id', copy=False)
    status_ids = fields.One2many(comodel_name='stock.picking.unifaun.status', inverse_name='unifaun_id', string='Unifaun Status')
    param_ids = fields.One2many(comodel_name='stock.picking.unifaun.param', inverse_name='unifaun_id', string='Parameters')
    parcel_count = fields.Integer(string='Unifaun Parcel Count', copy=False, help="Fill in this field to override package data. Will override data from packages if used.")
    parcel_weight = fields.Float(string='Unifaun Parcel Weight', copy=False, help="Fill in this field to override package data. Will override weight unless the data is generated from packages.")
    weight = fields.Float(string='Weight', digits_compute=dp.get_precision('Stock Weight'), compute='_calculate_weight', store=True)
    #weight_net = fields.Float(string='Net Weight', digits_compute=dp.get_precision('Stock Weight'), compute='_calculate_weight', store=True)
    #package_ids = fields.Many2many(comodel_name='stock.quant.package', compute='_compute_package_ids')
    carrier_id = fields.Many2one(comodel_name='Carrier', required=True)
    state = fields.Selection(string='State', select=[('draft', 'Draft'), ('sent', 'Sent'), ('done', 'Confirmed'), ('cancel', 'Cancelled'), ('error', 'Error')])
    picking_type_id = fields.Many2one(comodel_name='stock.picking.type', string='Picking Type', required=True)
    carrier_tracking_ref = fields.Char(string='Carrier Tracking Ref', copy=False)
    
    package_ids = fields.One2many(comodel_name='unifaun.package', inverse_name='unifaun_id', string='Packages')
    
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
    
    @api.multi
    def get_unifaun_sender_reference(self):
        return self.name 
    
    @api.one
    @api.depends(
        'package_ids.line_ids.qty',
        'package_ids.line_ids.uom_id',
        'package_ids.line_ids.product_id',
        'package_ids.spec_weight',
    )
    def _calculate_weight(self):
        if self.state == 'draft':
            weight = 0.00
            for package in self.package_ids:
                weight += package.spec_weight or package.weight
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
        self.unifaun_param_ids = None
        if self.carrier_id.is_unifaun and self.carrier_id.unifaun_param_ids:
            self.unifaun_param_ids = [(0, 0, d) for d in self.carrier_id.unifaun_param_ids.get_picking_param_values()]
            self.unifaun_param_ids.compute_default_value()
    
    @api.one
    def set_unifaun_status(self, statuses):
        if self.unifaun_status_ids:
            self.unifaun_status_ids.unlink()
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
        self.ensure_one()
        packages = []
        for package in self.package_ids:
            packages.append(package.unifaun_get_parcel_values())
        else:
            number_of_packages = self.unifaun_parcel_count or self.number_of_packages or 1
            weight = (self.unifaun_parcel_weight or self.weight) #/ number_of_packages # We're setting valuePerParcel to False, so this should be the total weight
            packages = [{
                'copies': number_of_packages,
                'weight': weight,
                'contents': _(self.env['ir.config_parameter'].get_param('unifaun.parcel_description', 'Goods')),
                'valuePerParcel': number_of_packages < 2,
            }]

        # TODO: add check
        min_weight = self.carrier_id.unifaun_min_weight
        if min_weight:
            for package in packages:
                package_min_weight = min_weight
                if not package.get('valuePerParcel'):
                    package_min_weight *= package['copies']
                if package['weight'] < package_min_weight:
                    package['weight'] = package_min_weight
        return packages
    
    @api.multi
    def unifaun_sender_record(self, sender):
        # ~ sender_contact = None
        # ~ if sender.parent_id and sender.type == 'contact':
            # ~ sender_contact = sender
            # ~ sender = self.env['res.partner'].browse(sender.parent_id.address_get(['delivery'])['delivery'])
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
        # ~ if sender_contact:
            # ~ rec.update({
                # ~ 'phone': sender_contact.phone or sender_contact.mobile or '',
                # ~ 'mobile': sender_contact.mobile or '',
                # ~ 'email': sender_contact.email or '',
                # ~ 'contact': sender_contact.name,
            # ~ })
        return rec
    
    @api.multi
    def unifaun_receiver_contact(self, receiver, current_values):
        """Contact info for the receiver record. Default is just to add the contact name, but could change phone number, email etc."""
        contact_data = {}
        if hasattr(self, 'sale_id'):
            contact_data['contact'] = self.sale_id.partner_id.name
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
            # ~ raise Warning(_('A stored shipment already exists for this order.'))
        #~ error = ''
        #~ #if not self.weight:
        #~ #    error += '\n' if error else ''
        #~ #    error += _('The delivery must have a weight.')
        #~ # TODO: Add more error handling
        #~ if error:
            #~ raise Warning(error)
        # Choose sender and receiver based on picking type (in or out).
        if self.picking_type_id.code == 'incoming':
            receiver = self.picking_type_id.warehouse_id.partner_id
            sender = self.partner_id
        elif self.picking_type_id.code == 'outgoing':
            sender = self.picking_type_id.warehouse_id.partner_id
            receiver = self.partner_id
        receiver_record = self.unifaun_receiver_record(receiver)
        receiver_record.update(self.unifaun_receiver_contact(receiver, receiver_record))
        rec = {
            'sender': self.unifaun_sender_record(sender),
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
        
        if self.unifaun_param_ids:
            self.unifaun_param_ids.add_to_record(rec)

        response = self.carrier_id.unifaun_send('stored-shipments', None, rec)
        printer = PrettyPrinter()
        if type(response) == dict:
            _logger.warn('\n%s\n' % response)
            self.unifaun_stored_shipmentid = response.get('id', '')

            self.env['mail.message'].create({
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s<br/>" % (printer.pprint(rec), printer.pprint(response))),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
            self.set_unifaun_status(response.get('statuses') or [])
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s<br/>" % (printer.pprint(rec), printer.pprint(response))),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.info('Unifaun Order Transport: rec %s response %s' % (printer.pprint(rec), printer.pprint(response)))

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
        response = self.carrier_id.unifaun_send('stored-shipments/%s/shipments' % self.unifaun_stored_shipmentid, None, rec)
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
                    unifaun_pdfs.append(r['pdfs'])
            self.carrier_tracking_ref = ', '.join(carrier_tracking_ref)
            self.shipmentid = ', '.join(unifaun_shipmentid)
            # create an attachment
            # TODO: several pdfs?
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
                    'picking_id': self.id,
                })
            
            self.env['mail.message'].create({
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s" % (rec, response)),
                'subject': "Shipment(s) Created",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
            self.unifaun_send_track_mail_silent()
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s" % (rec, response)),
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
        template_id = self.env.ref('delivery_unifaun_base.unifaun_email_template').id
        try:
            compose_form_id = self.env['ir.model.data'].get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'stock.picking',
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
