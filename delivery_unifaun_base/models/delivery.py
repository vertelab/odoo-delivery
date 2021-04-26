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
from odoo.tools.safe_eval import safe_eval
import requests
from requests.auth import HTTPBasicAuth
import json
import base64
# from urllib import urlencode
import traceback
import urllib3
from werkzeug import urls
import math
import pprint

import logging
_logger = logging.getLogger(__name__)

READ_ONLY_STATES = {'done': [('readonly', True)], 'sent': [('readonly', True)], 'cancel': [('readonly', True)]}


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

class UnifaunPackageLine(models.Model):
    _name = 'unifaun.package.line'
    _description = 'Unifaun Order Line'

    state = fields.Selection(related='unifaun_id.state')
    package_id = fields.Many2one(comodel_name='unifaun.package', string='Package', required=True, ondelete='cascade', states=READ_ONLY_STATES)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True, states=READ_ONLY_STATES)
    name = fields.Char(related='product_id.display_name', string="Name")
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure', required=True, states=READ_ONLY_STATES)
    qty = fields.Float(string='Quantity', states=READ_ONLY_STATES)
    product_qty = fields.Float(string='Product Quantity', compute='_calculate_product_qty')
    unifaun_id = fields.Many2one(related='package_id.unifaun_id')

    @api.depends('product_id', 'uom_id', 'qty')
    def _calculate_product_qty(self):
        uom_obj = self.env['uom.uom']
        for line in self:
            # TODO: Does this check work or will it be set to 0 if state != draft?
            if line.unifaun_id.state == 'draft':
                line.product_qty = uom_obj._compute_qty_obj(line.uom_id, line.qty, line.product_id.uom_id)


class UnifaunPackage(models.Model):
    _name = 'unifaun.package'
    _description = 'Unifaun Package'

    def _default_contents(self):
        return _(self.env['ir.config_parameter'].get_param('unifaun.parcel_description', 'Goods'))

    state = fields.Selection(related='unifaun_id.state')
    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order', required=True, ondelete='cascade', states=READ_ONLY_STATES)
    ul_id = fields.Many2one(comodel_name='product.packaging', string='Logistical Unit', states=READ_ONLY_STATES)
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging', help="This field should be completed only if everything inside the package share the same product, otherwise it doesn't really make sense.", states=READ_ONLY_STATES)
    shipper_package_code = fields.Char(string='Package Code', help="The shipping company's code for this packaging type.", states=READ_ONLY_STATES)
    line_ids = fields.One2many(comodel_name='unifaun.package.line', inverse_name='package_id', string='Products')
    name = fields.Char(string='Reference', states=READ_ONLY_STATES)
    contents = fields.Char(string='Contents', default=_default_contents, states=READ_ONLY_STATES)
    copies = fields.Integer(string='Copies', default=1, states=READ_ONLY_STATES)
    weight = fields.Float(string='Weight', compute='_calculate_weight', store=True, digits='Stock Weight')
    weight_calc = fields.Float(string='Weight Calc', compute='_calculate_weight', store=True, digits='Stock Weight')
    weight_spec = fields.Float(string='Specified Weight', digits='Stock Weight', help="Use this field to override the calculated weight.", states=READ_ONLY_STATES)

    @api.depends('line_ids.product_id', 'line_ids.uom_id',
                 'line_ids.qty', 'weight_spec')
    def _calculate_weight(self):
        """Calculate the weight of the packages. Includes boxes/pallets etc."""
        uom_obj = self.env['uom.uom']
        for package in self:
            # TODO: Does this check work or will it be set to 0 if state != draft?
            _logger.warn(self.unifaun_id.state)
            if package.unifaun_id.state == 'draft':
                weight = 0.00
                for line in package.line_ids:
                    weight += line.product_qty * line.product_id.weight
                # Box / Pallet
                if package.ul_id:
                    weight += package.ul_id.max_weight
                # Product distribution packages, e.g. boxes stapled on a pallet.
                if package.packaging_id:
                    weight += math.ceil(package.product_qty / package.packaging_id.qty) * package.packaging_id.ul.weight
                package.weight_calc = weight
                if package.weight_spec:
                    package.weight = package.weight_spec
                else:
                    package.weight = weight

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
            # package_code = self.ul_id.get_unifaun_package_code(self.carrier_id)
            package_code = self.ul_id.shipper_package_code
            if package_code:
                vals['packageCode'] = package_code
            #TODO: Add default package_code
        # TODO: Add volume, length, width, height
        return vals


class stock_picking_unifaun_status(models.Model):
    _name = 'stock.picking.unifaun.status'
    _description = 'Unifaun Status'

    field = fields.Char(string='field')
    name = fields.Char(string='message')
    type = fields.Char(string='type')
    location = fields.Char(string='location')
    message_code = fields.Char(string='messageCode')
    raw_data = fields.Char(string='Raw Data')
    picking_id = fields.Many2one(comodel_name='stock.picking')
    # ~ trans_id = fields.Many2one(comodel_name='stock.picking.unifaun.status_trans', string='Human Readable Message')
    # ~ trans_message = fields.Char(string='Message', related='trans_id.name')
    
    # ~ def translate_message(self):
        # ~ self.trans_id = self.env['stock.picking.unifaun.status_trans'].search([
            # ~ '|',
                # ~ ('field', '=', self.field),
                # ~ ('field', '=', '*'),
            # ~ '|',
                # ~ ('message', '=', self.name),
                # ~ ('message', '=', '*'),
            # ~ '|',
                # ~ ('type', '=', self.type),
                # ~ ('type', '=', '*'),
            # ~ '|',
                # ~ ('location', '=', self.location),
                # ~ ('location', '=', '*'),
            # ~ '|',
                # ~ ('message_code', '=', self.message_code),
                # ~ ('message_code', '=', '*'),
        # ~ ], limit=1)
    
    # ~ @api.model
    # ~ @api.returns('self', lambda value: value.id)
    # ~ def create(self, vals):
        # ~ res = super(stock_picking_unifaun_status, self).create(vals)
        # ~ res.translate_message()
        # ~ return res

# ~ #access_stock_stock_picking_unifaun_status_trans_user,access_stock_stock_picking_unifaun_status_trans_user,model_stock_picking_unifaun_status_trans,stock.group_stock_user,1,1,1,1
# ~ class stock_picking_unifaun_status_trans(models.Model):
    # ~ _name = 'stock.picking.unifaun.status_trans'
    # ~ _order = 'sequence'

    # ~ name = fields.Char(string='Message', required=True, translate=True)
    # ~ sequence = fields.Integer(string='Sequence', default=100)
    # ~ field = fields.Char(string='field')
    # ~ message = fields.Char(string='message')
    # ~ type = fields.Char(string='type')
    # ~ location = fields.Char(string='location')
    # ~ message_code = fields.Char(string='messageCode')

# Definition of format selection fields for DeliveryCarrierUnifaunPrintSettings
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
    
    format_1 = fields.Selection(string='Label Type Format 1', selection=print_format_selection, required=True, default='laser-a4')
    x_offset_1 = fields.Float(string='X Offset Format 1')
    y_offset_1 = fields.Float(string='Y Offset Format 1')
    
    format_2 = fields.Selection(string='Label Type Format 2', selection=print_format_selection, required=True, default='null')
    x_offset_2 = fields.Float(string='X Offset Format 2')
    y_offset_2 = fields.Float(string='Y Offset Format 2')
    
    format_3 = fields.Selection(string='Label Type Format 3', selection=print_format_selection, required=True, default='null')
    x_offset_3 = fields.Float(string='X Offset Format 3')
    y_offset_3 = fields.Float(string='Y Offset Format 3')
    
    format_4 = fields.Selection(string='Label Type Format 4', selection=print_format_selection, required=True, default='null')
    x_offset_4 = fields.Float(string='X Offset Format 4')
    y_offset_4 = fields.Float(string='Y Offset Format 4')

class DeliveryCarrierUnifaunParam(models.Model):
    _name = 'delivery.carrier.unifaun.param'
    _description = 'Unifaun Carrier Parameter'

    name = fields.Char(string='Name', required=True)
    carrier_id = fields.Many2one(comodel_name='delivery.carrier', string='Carrier', ondelete='cascade', required=True)
    parameter = fields.Char(string='Parameter', required=True)
    type = fields.Selection(selection=[('string', 'String'), ('int', 'Integer'), ('float', 'Float')], default='string', required=True)
    default_value = fields.Char(string='Default Value')
    default_compute = fields.Char(string='Default Compute', help="Expression to compute default value for this parameter. variable param = the parameter object. Example: 'param.picking_id.sale_id.name'")

    def get_default_value(self):
        try:
            if self.type == 'string':
                return {'value': self.default_value}
            elif not self.default_value:
                return False
            elif self.type == 'integer':
                return {'value': int(self.default_value)}
            elif self.type == 'float':
                return {'value': float(self.default_value)}
        except:
            raise Warning(_("Could not convert the default value (%s) to type %s") % (self.default_value, self.type))

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
    value_shown = fields.Char(string='Shown Value', compute='_get_value_shown', inverse='_set_value_shown')
    # ~ value_char = fields.Char(string='Value')
    # ~ value_int = fields.Integer(string='Value')
    # ~ value_float = fields.Float(string='Value')
    param_id =  fields.Many2one(comodel_name='delivery.carrier.unifaun.param', string='Carrier Parameter', ondelete='set null')

    @api.onchange('value')
    def _get_value_shown(self):
        self.value_shown = self.value

    def _set_value_shown(self):
        self.set_value(self.value_shown or None)
    
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

    def compute_default_value(self):
        if self.param_id and self.param_id.default_compute:
            self.set_value(safe_eval(self.param_id.default_compute, {'param': self}, locals_builtins=True))
    
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

class StockPickingUnifaunPdf(models.Model):
    _name = 'stock.picking.unifaun.pdf'
    _description = 'Unifaun PDF'
    
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
    
    @api.depends('quant_ids.quantity', 'quant_ids.product_id.weight')
    def _compute_weight(self):
        weight = self.ul_id and self.ul_id.max_weight or 0.0
        for quant in self.quant_ids:
            weight += quant.qty * quant.product_id.weight
        for pack in self.quant_ids:
            weight += pack.product_id.weight
        self.weight = weight
    
    @api.onchange('weight')
    def onchange_weight(self):
        self.shipping_weight = self.weight

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
    
    # TODO: This is the wrong packaging for this. It should be on the product.ul model.
    shipper_package_code = fields.Char(string='Shipper Packaging Ref')


class StockPackOperation(models.Model):
    _inherit = 'stock.move'
    
    result_package_working_weight = fields.Float(string='Working Weight', compute='_compute_working_weight', help="Calculated weight before package is finalized.")
    # result_package_weight = fields.Float(related='result_package_id.weight')
    result_package_weight = fields.Float(string="Package Weight")
    # result_package_shipping_weight = fields.Float(related='result_package_id.shipping_weight')
    result_package_shipping_weight = fields.Float(string="Shipping Weight")

    def _compute_working_weight(self):
        # TODO: Add support for packages in packages.
        if self.picking_id.state == 'assigned':
            # Packaging is not finalized. Calculate from packop lines.
            weight = 0.0
            if self.result_package_id:
                weight = self.result_package_id.ul_id and self.result_package_id.ul_id.max_weight or 0.0
                for op in self.picking_id.move_lines.filtered(lambda o: o.result_package_id == self.result_package_id):
                    qty = op.product_uom_id._compute_quantity(op.product_uom_id, op.product_qty, op.product_id.uom_id)
                    weight += qty * op.product_id.weight
            self.result_package_working_weight = weight
        else:
            self.result_package_working_weight = self.result_package_weight
            
class unifaun_parcel_weight(models.Model):
    _name = 'unifaun.parcel.weight'
    _description = 'Unifaun Parcel Weight Desc'

    weight = fields.Float(string='Weight')
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Picking')

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
    weight = fields.Float(string='Weight', digits='Stock Weight', compute='_calculate_weight', store=True)
    weight_net = fields.Float(string='Net Weight', digits='Stock Weight', compute='_calculate_weight', store=True)
    unifaun_parcel_weight_ids = fields.One2many(comodel_name='unifaun.parcel.weight', inverse_name='picking_id',
                                                copy=False, string="Unifan Parcel Weight Lines")
    sender_contact_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact Person',
        
        ) 
    receiver_contact_id = fields.Many2one(
        comodel_name='res.partner',
        string='Recipient Contact',
        ) 

    
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
    
    def get_unifaun_sender_reference(self):
        return self.name 
    
    @api.depends(
        'move_lines.state',
        'move_lines.product_id',
        'move_lines.product_uom_qty',
        'move_lines.product_uom',
        # 'move_line_ids.result_package_id.quant_ids',
        # 'move_line_ids.result_package_id.quant_ids.quantity',
        # 'move_line_ids.result_package_id.quant_ids.product_id.weight',
        'move_line_ids.product_uom_id',
        'move_line_ids.product_qty',
        'move_line_ids.product_id.uom_id'
    )
    def _calculate_weight(self):
        total_weight = total_weight_net = 0.00
        # Original weight calculation
        for move in self.move_lines:
            if move.state != 'cancel':
                total_weight += move.weight
                # total_weight_net += move.weight_net
        # Package weights
        if self.move_lines:
            total_weight = 0.00
        # Package weights
        for package in self.package_ids:
            total_weight += package.shipping_weight or package.weight or 0
        # Pack operations weight (except packages)
        for op in self.move_lines.move_line_ids.filtered(lambda o: not o.result_package_id):
            qty = op.product_uom_id._compute_quantity(op.product_qty, op.product_id.uom_id)
            # qty = op.product_uom_id._compute_quantity(op.product_uom_id, op.product_qty, op.product_id.uom_id)
            total_weight += op.product_id.weight * qty
        self.weight = total_weight
        self.weight_net = total_weight_net
    
    # https://www.unifaunonline.se/rs-docs/
    # Create shipment to be completed manually
    # catch carrier_tracking_ref (to be mailed? add on waybill)
    
    # ~ @api.depends('pack_operation_ids.result_package_id')
    def _compute_package_ids(self):
        self.package_ids = self.move_lines.move_line_ids.mapped('result_package_id')
        
    @api.onchange('carrier_id')
    def onchange_carrier(self):
        self.unifaun_param_ids = None
        if self.carrier_id.is_unifaun and self.carrier_id.unifaun_param_ids:
            self.unifaun_param_ids = [(0, 0, d) for d in self.carrier_id.unifaun_param_ids.get_picking_param_values()]
            self.unifaun_param_ids.compute_default_value()
            
    
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
            
            res = 'https://www.unifaunonline.com/ext.uo.%s.%s.track?&%s' % (region, lang, urls.url_encode(parameters).
                                                                            replace('&amp;', '&'))
        else:
            res = ''
        
        return res


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
                'packageCode':self.carrier_id.unifaun_param_ids.default_value,
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
    
    def unifaun_sender_record(self, sender):
        sender_contact = None
        if sender.parent_id and sender.type == 'contact':
            sender_contact = sender
            sender = self.env['res.partner'].browse(sender.parent_id.address_get(['delivery'])['delivery'])
        rec = {
                'contact': sender.name,
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
    
    def unifaun_receiver_contact(self, receiver, current_values):
        """Contact info for the receiver record. Default is just to add the contact name, but could change phone number, email etc."""
        contact_data = {}
        if hasattr(self, 'sale_id'):
            contact_data['contact'] = self.sale_id.partner_id.name
        return contact_data
        
    def unifaun_sender_contact(self, sender, current_values):
        """Contact info for the receiver record. Default is just to add the contact name, but could change phone number, email etc."""
        contact_data = {}
        if self.sender_contact_id:
            contact_data['contact'] = self.sender_contact_id.name
        return contact_data
    
    def unifaun_receiver_record(self, receiver):
        rec = {
                'contact': receiver.name,
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
        sender_record = self.unifaun_sender_record(sender)
        sender_record.update(self.unifaun_sender_contact(sender, sender_record))
        receiver_contact_info = self.partner_id
        sender_contact_info = self.picking_type_id.warehouse_id.sender_contact_id
        rec = {
            
            'sender': sender_record,
            'contact': sender_contact_info and sender_contact_info.id or None,
            'senderPartners': [{
                'id': self.carrier_id.unifaun_sender or '',
                'custNo': self.carrier_id.unifaun_customer_no or '',
            }],
            'receiver': receiver_record,
            'contact': receiver_contact_info and receiver_contact_info.id or None,
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
        digits='Stock Weight',
        compute='_calculate_weight',
        store=True)
    carrier_id = fields.Many2one(comodel_name='delivery.carrier', string='Carrier', required=True)
    carrier_tracking_ref = fields.Char(string='Carrier Tracking Ref', copy=False)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.picking'))
    date = fields.Datetime(
        string='Date',
        help="The planned date of the delivery",
        states=READ_ONLY_STATES,
        tracking=True
    )
    package_ids = fields.One2many(comodel_name='unifaun.package', inverse_name='unifaun_id', string='Packages')
    line_ids = fields.One2many(related='package_ids.line_ids', string='Package Contents')

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
                for op in picking.move_lines:
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
            for op in pickings.mapped('pack_operation_ids').filtered(lambda op: op.package_id == package.id):
                values['line_ids'].append((0, 0, op.unifaun_package_line_values()))
            packages.append((0, 0, values))
        ### Check for packops not in packages ###
        pack_ops = []
        # Handle pickings that should all be their own package
        for picking in pickings.filtered('unifaun_own_package'):
            ops = picking.move_lines.filtered(lambda o: not o.result_package_id)
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

    def get_unifaun_sender_reference(self):
        return self.name

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
                'raw_data': u'%s' % d,
                'unifaun_id': self.id,
            })
        # ~ {u'field': u'Party_CustNo', u'message': u'invalid check digit', u'type': u'error', u'location': u'', u'messageCode': u'Checkdigit'}

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

            res = 'https://www.unifaunonline.com/ext.uo.%s.%s.track?&%s' % (
            region, lang, urls.url_encode(parameters).replace('&amp;', '&'))
        else:
            res = ''
        return res

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

    def unifaun_receiver_contact(self, receiver, current_values):
        """Contact info for the receiver record. Default is just to add the contact name, but could change phone number, email etc."""
        contact_data = {}
        if self.contact_partner_id:
            contact_data['contact'] = self.contact_partner_id.name
        return contact_data

    def unifaun_sender_contact(self, sender, current_values):
        """Contact info for the receiver record. Default is just to add the contact name, but could change phone number, email etc."""
        contact_data = {}
        if self.sender_contact_id:
            contact_data['contact'] = self.sender_contact_id.name
        return contact_data

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
            # ~ "receiverReference": "receiver ref 345",
            # ~ "options": [{
            # ~ "message": "This is order number 123",
            # ~ "to": "sales@unifaun.com",
            # ~ "id": "ENOT",
            # ~ "languageCode": "SE",
            # ~ "from": "info@unifaun.com"
            # ~ }],
        }

        if self.param_ids:
            self.param_ids.add_to_record(rec)

        response = self.carrier_id.unifaun_send('stored-shipments', None, rec)
        # printer = PrettyPrinter()
        if type(response) == dict:
            _logger.warn('\n%s\n' % response)
            self.stored_shipmentid = response.get('id', '')

            self.env['mail.message'].create({
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s<br/>" % (pprint.pformat(rec), pprint.pformat(response))),
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
                'body': _(
                    "Unifaun error!<br/>rec %s<br/>resp %s<br/>" % (pprint.pformat(rec), pprint.pformat(response))),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.info('Unifaun Order Transport: rec %s response %s' % (rec, response))

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
        # printer = PrettyPrinter()
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
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s" % (pprint.pformat(rec), pprint.pformat(response))),
                'subject': "Shipment(s) Created",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
            self.unifaun_send_track_mail_silent()
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s" % (pprint.pformat(rec), pprint.pformat(response))),
                'subject': "Create Shipment",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.info('Unifaun Order Transport: rec %s response %s' % (rec, response))

    def unifaun_send_track_mail(self):
        self.ensure_one()
        template_id = self.env.ref('delivery_unifaun_base.unifaun_order_email_template').id
        try:
            compose_form_id = \
            self.env['ir.model.data'].get_object_reference('mail', 'email_compose_message_wizard_form')[1]
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

    def unifaun_send_track_mail_silent(self):
        if self.env.context.get('unifaun_track_force_send') or self.env['ir.config_parameter'].get_param(
                'unifaun.sendemail', '1') == '1':
            template = self.env.ref('delivery_unifaun_base.unifaun_email_template')
            try:
                template.send_mail(self.id)
            except:
                self.env['mail.message'].create({
                    'body': _(
                        "Mail error!<br/>Could not send email<br/>%s" % traceback.format_exc().replace('\n', '<br/>')),
                    'subject': "Send tracking mail",
                    'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                    'res_id': self.id,
                    'model': self._name,
                    'type': 'notification',
                })

