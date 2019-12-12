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
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.tools import safe_eval
from odoo.addons import decimal_precision as dp
import requests
from requests.auth import HTTPBasicAuth
import json
import base64
from urllib import urlencode
import traceback

import logging
_logger = logging.getLogger(__name__)


class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    # TODO: Implement models for SenderPartner and Service Code.
    # We need them to properly handle various stuff, such as packaging
    # codes, and other code list items.
    unifaun_service_code = fields.Char('Service Code')
    is_unifaun = fields.Boolean('Is Unifaun')
    unifaun_sender = fields.Char(string='SenderPartners id', help="Code describing the carrier. See Unifaun help pages.")
    unifaun_customer_no = fields.Char(string='Customer Number', help="The paying party's customer number with the carrier.")
    unifaun_param_ids = fields.One2many(comodel_name='delivery.carrier.unifaun.param', inverse_name='carrier_id', string='Parameters')
    unifaun_print_settings_id = fields.Many2one(comodel_name='delivery.carrier.unifaun.print_settings', string='Unifaun Print Settings')
    unifaun_min_weight = fields.Float(string='Minimum weight per package', help="The minimum weight per package allowed. Lower weights will be set to the minimum value.", default=0.00)
    #~ unifaun_environment = fields.Selection(string='Environment', selection=[('test', 'Test'), ('prod', 'Production')], default='test')

    #~ @api.multi
    #~ def test_environment(self):
        #~ self.ensure_one()
        #~ if 'test' in (self.env['ir.config_parameter'].get_param('unifaun.environment', 'prod'), self.unifaun_environment):
            #~ return True
        #~ return False

    def unifaun_download(self, pdf):
        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        response = requests.get(pdf['href'], auth=HTTPBasicAuth(username, password))
        return self.env['ir.attachment'].create({
            'type': 'binary',
            'name': 'Unifaun %s %s.pdf' % (pdf['description'], pdf['href'].split("/")[-1]),
            'mimetype': 'application/pdf',
            'datas': base64.b64encode(response.content),
        })


    def _unifaun_get_params(self):
        """ Return unifaun url, headers and auth parameters."""
        return self.env['ir.config_parameter'].get_param('unifaun.url'), {
                'headers': {'content-type': 'application/json'},
                'auth': HTTPBasicAuth(
                    self.env['ir.config_parameter'].get_param('unifaun.api_key'),
                    self.env['ir.config_parameter'].get_param('unifaun.passwd'))
            }

    def unifaun_delete(self, url_delete):
        url, req_params = self._unifaun_get_params()
        response = requests.delete(url + url_delete,
            verify=False,
            **req_params)
        _logger.warn(response)
        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("unifaun_delete (%s) ERROR %s: %s" % (url_delete, response.status_code, response.text))
            return False, response
        return True, response

    def unifaun_send(self, method, params=None, payload=None):
        url, req_params = self._unifaun_get_params()
        response = requests.post(
            url + '/' + method,
            params=params,
            data=payload and json.dumps(payload) or None,
            verify=False,
            **req_params)

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}

        return response.json()

    def unifaun_receive(self, method, params=None):
        headers = {'content-type': 'application/json'}

        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        url = self.env['ir.config_parameter'].get_param('unifaun.url')

        response = requests.get(
            url + '/' + method,
            params=params,
            headers=headers,
            verify=False,
            auth=HTTPBasicAuth(username, password))

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}

        return response.json()

    def get_file(self, url):
        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        response = requests.get(
            url,
            verify=False,
            auth=HTTPBasicAuth(username, password))
        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}

        return response.content


class stock_picking_unifaun_status(models.Model):
    _name = 'stock.picking.unifaun.status'

    field = fields.Char(string='field')
    name = fields.Char(string='message')
    type = fields.Char(string='type')
    location = fields.Char(string='location')
    message_code = fields.Char(string='messageCode')
    raw_data = fields.Char(string='Raw Data')
    picking_id = fields.Many2one(comodel_name='stock.picking')

print_format_selection = [
        ('null', 'None'),
        ('laser-a5', 'Single A5 label'),
        ('laser-2a5', 'Two A5 labels on A4 paper'),
        ('laser-ste', 'Two STE labels (107x251 mm) on A4 paper'),
        ('laser-a4', 'Normal A4 used for waybills, customs declaration documents etc.'),
        ('thermo-se', '107 x 251 mm thermo STE label'),
        ('thermo-190', '107 x 190 mm thermo label'),
        ('thermo-brev3', '107 x 72 mm thermo label'),
        ('thermo-165', '107 x 165 mm thermo label')
    ]

class DeliveryCarrierUnifaunPrintSettings(models.Model):
    _name = 'delivery.carrier.unifaun.print_settings'
    _description = 'Unifaun Print Settings'
    
    name = fields.Char(string='Name', required=True)
    
    format_1 = fields.Selection(string='Label Type', selection=print_format_selection, required=True, default='laser-a4')
    x_offset_1 = fields.Float(string='X Offset')
    y_offset_1 = fields.Float(string='Y Offset')
    
    format_2 = fields.Selection(string='Label Type', selection=print_format_selection, required=True, default='null')
    x_offset_2 = fields.Float(string='X Offset')
    y_offset_2 = fields.Float(string='Y Offset')
    
    format_3 = fields.Selection(string='Label Type', selection=print_format_selection, required=True, default='null')
    x_offset_3 = fields.Float(string='X Offset')
    y_offset_3 = fields.Float(string='Y Offset')
    
    format_4 = fields.Selection(string='Label Type', selection=print_format_selection, required=True, default='null')
    x_offset_4 = fields.Float(string='X Offset')
    y_offset_4 = fields.Float(string='Y Offset')

class DeliveryCarrierUnifaunParam(models.Model):
    _name = 'delivery.carrier.unifaun.param'
    _description = 'Unifaun Carrier Parameter'

    name = fields.Char(string='Name', required=True)
    carrier_id = fields.Many2one(comodel_name='delivery.carrier', string='Carrier', ondelete='cascade', required=True)
    parameter = fields.Char(string='Parameter', required=True)
    type = fields.Selection(selection=[('string', 'String'), ('int', 'Integer'), ('float', 'Float')], default='string', required=True)
    default_value = fields.Char(string='Default Value')
    default_compute = fields.Char(string='Default Compute', help="Expression to compute default value for this parameter. variable param = the parameter object. Example: 'param.picking_id.sale_id.name'")

    @api.multi
    def get_default_value(self):
        try:
            if self.type == 'string':
                return {'value_char': self.default_value}
            elif not self.default_value:
                return False
            elif self.type == 'integer':
                return {'value_int': int(self.default_value)}
            elif self.type == 'float':
                return {'value_float': float(self.default_value)}
        except:
            raise Warning(_("Could not convert the default value (%s) to type %s") % (self.default_value, self.type))

    @api.multi
    def get_picking_param_values(self):
        values = []
        for param in self:
            vals = {
                'name': param.name,
                'parameter': param.parameter,
                'type': param.type,
                'param_id': param.id,
            }
            vals.update(param.get_default_value())
            values.append(vals)
        return values

class StockPickingUnifaunParam(models.Model):
    _name = 'stock.picking.unifaun.param'
    _description = 'Unifaun Picking Parameter'

    name = fields.Char(string='Name', required=True)
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Picking', required=True, ondelete='cascade')
    parameter = fields.Char(string='Parameter', required=True)
    type = fields.Selection(selection=[('string', 'String'), ('int', 'Integer'), ('float', 'Float')], default='string', required=True)
    value = fields.Char(string='Value')
    value_shown = fields.Char(string='Value', compute='_get_value_shown', inverse='_set_value_shown')
    # ~ value_char = fields.Char(string='Value')
    # ~ value_int = fields.Integer(string='Value')
    # ~ value_float = fields.Float(string='Value')
    param_id =  fields.Many2one(comodel_name='delivery.carrier.unifaun.param', string='Carrier Parameter', ondelete='set null')

    @api.one
    def _get_value_shown(self):
        self.value_shown = self.value

    @api.one
    def _set_value_shown(self):
        self.set_value(self.value_shown or None)
    
    @api.multi
    def get_value(self):
        try:
            if self.type == 'string':
                return self.value
            elif self.type == 'int':
                return self.value and int(self.value) or None
            elif self.type == 'float':
                return self.value and float(self.value) or None
        except:
            raise Warning(_("Could not convert the value (%s) of parameter %s to type %s") % (self.value, self.name, self.type))
        raise Warning(_("Unknown type %s for parameter %s (%s)") % (self.type, self.name, self.parameter))

    @api.one
    def set_value(self, value):
        if value in (None, False):
            self.value = value
            return
        try:
            if self.type == 'string':
                self.value = value
                return
            elif self.type == 'int':
                self.value = str(int(value))
                return
            elif self.type == 'float':
                self.value = str(float(value))
                return
        except:
            raise Warning(_("Could not convert the value (%s, type %s) of parameter %s to type %s") % (value, type(value), self.name, self.type))
        raise Warning(_("Unknown type %s for parameter %s (%s)") % (self.type, self.name, self.parameter))

    @api.one
    def compute_default_value(self):
        if self.param_id and self.param_id.default_compute:
            self.set_value(safe_eval(self.param_id.default_compute, {'param': self}, locals_builtins=True))
    
    @api.multi
    def add_to_record(self, rec):
        """Add this parameter to the given dict"""
        def split_parameter(parameter):
            if '.' in parameter:
                return parameter.split('.', 1)
            else:
                return parameter, None

        def write_param(node, value, parameter):
            if type(node) == list:
                if not node:
                    # Create an object for the next level. Maybe not the desired result?
                    node.append({})
                for e in node:
                    write_param(e, value, parameter)
                return
            name, parameter = split_parameter(parameter)
            is_list = False
            if name[-2:] == '[]':
                is_list = True
                name = name[:-2]
            if name not in node:
                if is_list:
                    node[name] = []
                elif parameter:
                    node[name] = {}
                else:
                    node[name] = value
                    return
            elif not parameter:
                node[name] = value
                return
            write_param(node[name], value, parameter)

        for param in self:
            value = param.get_value()
            write_param(rec, param.get_value(), param.parameter)
class StockPickingUnifuanPdf(models.Model):
    _name = 'stock.picking.unifaun.pdf'
    
    name = fields.Char(string='Description', required=True)
    href = fields.Char(string='Href')
    unifaunid = fields.Char(string='Unifaun ID')
    attachment_id = fields.Many2one(string='PDF', comodel_name='ir.attachment', required=True)
    picking_id = fields.Many2one(string='Picking', comodel_name='stock.picking', required=True, ondelete='cascade')
    
class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"
    
    unifaun_parcelno = fields.Char(string='Unifaun Reference')
    weight = fields.Float(string='Weight', compute='_compute_weight')
    shipping_weight = fields.Float(string='Shipping Weight', help="Can be changed during the 'put in pack' to adjust the weight of the shipping.")
    
    @api.one
    @api.depends('quant_ids.qty', 'quant_ids.product_id.weight', 'children_ids')
    def _compute_weight(self):
        weight = self.ul_id and self.ul_id.weight or 0.0
        for quant in self.quant_ids:
            weight += quant.qty * quant.product_id.weight
        for pack in self.children_ids:
            weight += pack.weight
        self.weight = weight
    
    @api.onchange('weight')
    def onchange_weight(self):
        self.shipping_weight = self.weight

    @api.multi
    def unifaun_get_parcel_values(self):
        """Return a dict of parcel data to be used in a Unifaun shipment record."""
        vals = {
            'reference': self.name, # ??? Not saved in shipment
            'copies': 1,
            'weight': self.shipping_weight or self.weight or 0,
            'contents': _(self.env['ir.config_parameter'].get_param('unifaun.parcel_description', 'Goods')),
            'valuePerParcel': True,
        }
        if self.packaging_id:
            if self.packaging_id.shipper_package_code:
                vals['packageCode'] = self.packaging_id.shipper_package_code
            # TODO: Add volume, length, width, height
        return vals

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'
    
    shipper_package_code = fields.Char(string='Shipper Packaging Ref')

class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'
    
    result_package_working_weight = fields.Float(string='Working Weight', compute='_compute_working_weight', help="Calculated weight before package is finalized.")
    result_package_weight = fields.Float(related='result_package_id.weight')
    result_package_shipping_weight = fields.Float(related='result_package_id.shipping_weight')
    
    @api.one
    def _compute_working_weight(self):
        # TODO: Add support for packages in packages.
        if self.picking_id.state == 'assigned':
            # Packaging is not finalized. Calculate from packop lines.
            weight = 0.0
            if self.result_package_id:
                weight = self.result_package_id.ul_id and self.result_package_id.ul_id.weight or 0.0
                for op in self.picking_id.pack_operation_ids.filtered(lambda o: o.result_package_id == self.result_package_id):
                    qty = op.product_uom_id._compute_quantity(op.product_qty, op.product_id.uom_id)
                    # qty = op.product_uom_id._compute_qty_obj(op.product_uom_id, op.product_qty, op.product_id.uom_id)
                    weight += qty * op.product_id.weight
            self.result_package_working_weight = weight
        else:
            self.result_package_working_weight = self.result_package_weight

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    is_unifaun = fields.Boolean(related='carrier_id.is_unifaun')
    unifaun_shipmentid = fields.Char(string='Unifaun Shipment ID', copy=False)
    unifaun_stored_shipmentid = fields.Char(string='Unifaun Stored Shipment ID', copy=False)
    unifaun_pdf_ids = fields.One2many(string='Unifaun PDFs', comodel_name='stock.picking.unifaun.pdf', inverse_name='picking_id', copy=False)
    unifaun_status_ids = fields.One2many(comodel_name='stock.picking.unifaun.status', inverse_name='picking_id', string='Unifaun Status')
    unifaun_param_ids = fields.One2many(comodel_name='stock.picking.unifaun.param', inverse_name='picking_id', string='Parameters')
    unifaun_parcel_count = fields.Integer(string='Unifaun Parcel Count', copy=False, help="Fill in this field to override package data. Will override data from packages if used.")
    unifaun_parcel_weight = fields.Float(string='Unifaun Parcel Weight', copy=False, help="Fill in this field to override package data. Will override weight unless the data is generated from packages.")
    package_ids = fields.Many2many (comodel_name='stock.quant.package', compute='_compute_package_ids')
    weight = fields.Float(string='Weight', digits_compute= dp.get_precision('Stock Weight'), compute='_calculate_weight', store=True)
    weight_net = fields.Float(string='Net Weight', digits_compute= dp.get_precision('Stock Weight'), compute='_calculate_weight', store=True)
    

    
    @api.multi
    def get_unifaun_language(self):
        translate = {
            'en_US': 'gb',
            'sv_SE': 'se',
            'no_NO': 'no',
            'nn_NO': 'no',
            'nb_NO': 'no',
            'fi_FI': 'fi',
            'da-DK': 'dk'
        }
        
        return translate.get(self.partner_id.lang,'gb') 
    
    @api.multi
    def get_unifaun_sender_reference(self):
        return self.name 
    
    @api.one
    @api.depends(
        'move_lines.state',
        'move_lines.product_id',
        'move_lines.product_uom_qty',
        'move_lines.product_uom',
        'pack_operation_ids.result_package_id.quant_ids',
        'pack_operation_ids.result_package_id.children_ids',
        'pack_operation_ids.result_package_id.quant_ids.qty',
        'pack_operation_ids.result_package_id.quant_ids.product_id.weight',
        'pack_operation_ids.product_uom_id',
        'pack_operation_ids.product_qty',
        'pack_operation_ids.product_id.uom_id'
    )
    def _calculate_weight(self):
        total_weight = total_weight_net = 0.00
        # Original weight calculation
        for move in self.move_lines:
            if move.state != 'cancel':
                total_weight += move.weight
                # total_weight_net += move.weight_net
                total_weight_net += move.weight #TODO this should be weight_net
        # Package weights
        if self.pack_operation_ids:
            total_weight = 0.00
        # Package weights
        for package in self.package_ids:
            total_weight += package.shipping_weight or package.weight or 0
        # Pack operations weight (except packages)
        for op in self.pack_operation_ids.filtered(lambda o: not o.result_package_id):
            qty = op.product_uom_id._compute_quantity(op.product_qty, op.product_id.uom_id)
            # qty = op.product_uom_id._compute_qty_obj(op.product_uom_id, op.product_qty, op.product_id.uom_id)
            total_weight += op.product_id.weight * qty
        self.weight = total_weight
        self.weight_net = total_weight_net

    # https://www.unifaunonline.se/rs-docs/
    # Create shipment to be completed manually
    # catch carrier_tracking_ref (to be mailed? add on waybill)
    
    @api.one
    # ~ @api.depends('pack_operation_ids.result_package_id')
    def _compute_package_ids(self):
        self.package_ids = self.pack_operation_ids.mapped('result_package_id')

    @api.onchange('carrier_id')
    def onchange_carrier(self):
        # super(stock_picking, self).onchange_carrier()
        self.unifaun_param_ids = None
        if self.carrier_id.is_unifaun and self.carrier_id.unifaun_param_ids:
            self.unifaun_param_ids = [(0, 0, d) for d in self.carrier_id.unifaun_param_ids.get_picking_param_values()]
            self.unifaun_param_ids.compute_default_value()
            
    
    @api.one
    def set_unifaun_status(self, statuses):
        if len(self.unifaun_status_ids) > 0:
            self.env['stock.picking.unifaun.status'].browse(self.unifaun_status_ids.mapped('id')).unlink()
        self.unifaun_status_ids = self.env['stock.picking.unifaun.status'].browse([])
        for d in statuses:
            self.env['stock.picking.unifaun.status'].create({
                'field': d.get('field'),
                'name': d.get('message'),
                'type': d.get('type'),
                'location': d.get('location'),
                'message_code': d.get('messageCode'),
                'raw_data': u'%s' %d,
                'picking_id': self.id,
            })
        # ~ {u'field': u'Party_CustNo', u'message': u'invalid check digit', u'type': u'error', u'location': u'', u'messageCode': u'Checkdigit'}

    @api.multi
    def unifaun_track_and_trace_url(self):
        """Return an URL for Unifaun Track & Trace."""
        # https://www.unifaunonline.se/ufoweb-prod-201812111106/public/SUP/UO/UO-101-TrackandTrace-en.pdf
        # TODO: Add support for regions (what does regions even do?)
        if self.is_unifaun and self.unifaun_shipmentid:
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

        if self.package_ids and not self.unifaun_parcel_count:
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
        if self.unifaun_shipmentid:
            raise Warning(_('The stored shipment has already been confirmed (there is a Shipment id).'))
        if self.unifaun_stored_shipmentid:
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
            'parcels': self.unifaun_get_parcel_data(),
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
        if type(response) == type({}):
            _logger.warn('\n%s\n' % response)
            self.unifaun_stored_shipmentid = response.get('id', '')

            self.env['mail.message'].create({
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
            self.set_unifaun_status(response.get('statuses') or [])
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.info('Unifaun Order Transport: rec %s response %s' % (rec,response))

    @api.one
    def delete_stored_shipment(self):
        if not self.unifaun_stored_shipmentid:
            raise Warning(_('No stored shipment found for this order.'))
        if self.unifaun_shipmentid:
            raise Warning(_('The stored shipment has already been confirmed (there is a Shipment id).'))
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        res, response = self.carrier_id.unifaun_delete('/stored-shipments/%s' % self.unifaun_stored_shipmentid)
        if res:
            self.unifaun_stored_shipmentid = None
        else:
            message = _('Failed to delete stored shipment %s!' % self.unifaun_stored_shipmentid)
            if response.status_code == 404:
                message += _('\n\n404: Stored shipment not found')
            else:
                message += _('\n\n%s: %s') % (response.status_code, response.text)
            raise Warning(message)

    @api.one
    def confirm_stored_shipment(self):
        """Create shipment(s) from a stored shipment."""
        if not self.unifaun_stored_shipmentid:
            raise Warning(_('No stored shipment found for this order.'))
        if self.unifaun_shipmentid:
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
            unifaun_shipmentid = ''
            carrier_tracking_ref = ''
            unifaun_pdfs = []
            parcels = 0
            for r in response:
                # Could be more than one shipment.
                if carrier_tracking_ref:
                    carrier_tracking_ref += ', '
                carrier_tracking_ref += r.get('shipmentNo') or ''
                if unifaun_shipmentid:
                    unifaun_shipmentid += ', '
                unifaun_shipmentid += r.get('id') or ''
                if r.get('pdfs'):
                    unifaun_pdfs += r['pdfs']
                for parcel in r.get('parcels') or []:
                    parcels += 1
                if self.package_ids and r.get('parcels'):
                    i = 0
                    for package in self.package_ids:
                        if i < len(r['parcels']):
                            package.unifaun_parcelno = r['parcels'][i].get(u'parcelNo')
                        i += 1
            self.number_of_packages = parcels
            self.carrier_tracking_ref = carrier_tracking_ref
            self.unifaun_shipmentid = unifaun_shipmentid
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
