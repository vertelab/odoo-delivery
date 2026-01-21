# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2017 Tiny SPRL (<http://tiny.be>).
#       
#    Third party addon by Vertel AB
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

from io import BytesIO
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.service import common

import requests
from lxml import etree

import logging

_logger = logging.getLogger(__name__)

FRAKTJAKT_API_VERSION = '4.4'


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    is_fraktjakt = fields.Boolean('Is Fraktjakt')
    fraktjakt_id = fields.Char(string='Fraktjakt ID')
    fraktjakt_desc = fields.Char(string='Fraktjakt Description')
    partner_id = fields.Many2one(comodel_name='res.partner')

    def fraktjakt_send(self, method, payload=None):

        url = self.env['ir.config_parameter'].get_param('fraktjakt.turl' if self.env['ir.config_parameter'].get_param(
            'fraktjakt.environment') == 'test' else 'fraktjakt.purl')
        response = requests.get(url + '/' + method, params='xml=%s' % payload)

        if response.status_code < 200 or response.status_code >= 300:
            return response, response.status_code, response.text

        record = etree.XML(response.content)
        code = record.find('code').text
        warning = record.find('warning_message').text
        error = record.find('error_message').text
        if code == '1':
            _logger.warning("Fraktjakt Warning %s" % warning)
        elif code == '2':
            _logger.error("Fraktjakt Error %s" % error)
            return response, '2', error

        return response, '0', warning or 'OK'

    def init_element(self, tag):
        tree = etree.Element(tag)
        et = etree.ElementTree(tree)
        f = BytesIO()
        et.write(f, encoding='utf-8', xml_declaration=True)
        return tree

    def init_subelement(self, element, tag):
        return etree.SubElement(element, tag)

    def add_subelement(self, element, tag, value):
        sub = etree.SubElement(element, tag)
        sub.text = str(value)

    def add_consignor(self, shipment):
        consignor = etree.SubElement(shipment, 'consignor')
        self.add_subelement(consignor, 'id', self.env['ir.config_parameter'].get_param(
            'fraktjakt.tid' if self.env['ir.config_parameter'].get_param(
                'fraktjakt.environment') == 'test' else 'fraktjakt.pid'))
        self.add_subelement(consignor, 'key', self.env['ir.config_parameter'].get_param(
            'fraktjakt.tkey' if self.env['ir.config_parameter'].get_param(
                'fraktjakt.environment') == 'test' else 'fraktjakt.pkey'))
        self.add_subelement(consignor, 'currency', 'SEK')
        self.add_subelement(consignor, 'language', 'sv')
        self.add_subelement(consignor, 'encoding', 'utf-8')
        self.add_subelement(consignor, 'system_name', 'Odoo')
        self.add_subelement(consignor, 'system_version', common.exp_version()['server_serie'])
        self.add_subelement(consignor, 'module_version',
                            self.env.ref('base.module_delivery_fraktjakt').installed_version)
        self.add_subelement(consignor, 'api_version', FRAKTJAKT_API_VERSION)

    def add_address(self, element, tag, partner, residential=1):
        adress = self.init_subelement(element, tag)

        self.add_subelement(adress, 'street_address_1', partner.street or '')
        self.add_subelement(adress, 'street_address_2', partner.street2 or '')
        self.add_subelement(adress, 'postal_code', partner.zip or '')
        self.add_subelement(adress, 'city_name', partner.city or '')
        self.add_subelement(adress, 'residential', residential)
        self.add_subelement(adress, 'country_code', partner.country_id.code or 'SE')

    def get_url(self, method):
        pid = self.env['ir.config_parameter'].get_param('fraktjakt.tid' if self.env['ir.config_parameter'].get_param(
            'fraktjakt.environment') == 'test' else 'fraktjakt.pid')
        key = self.env['ir.config_parameter'].get_param('fraktjakt.tkey' if self.env['ir.config_parameter'].get_param(
            'fraktjakt.environment') == 'test' else 'fraktjakt.pkey')
        url = self.env['ir.config_parameter'].get_param('fraktjakt.turl' if self.env['ir.config_parameter'].get_param(
            'fraktjakt.environment') == 'test' else 'fraktjakt.purl')
        return '%s/%s?consignor_id=%s&consignor_key=%s' % (url, method, pid, key)


class DeliveryPackage(models.TransientModel):
    _inherit = "choose.delivery.package"

    fraktjakt_package_type = fields.Selection([
        ('pallet', 'Pallet'), ('half_pallet', 'Half Pallet'), ('others', 'Others')
    ], string="Package Type", default='pallet', required=True,
        related='delivery_package_type_id.fraktjakt_package_type')

    height = fields.Integer('Height', help="Packaging Height")

    def action_put_in_pack(self):
        move_line_ids = self.picking_id._package_move_lines(batch_pack=self.env.context.get("batch_pack"))
        delivery_package = self.picking_id._put_in_pack(move_line_ids)
        # write shipping weight and package type on 'stock_quant_package' if needed
        if self.delivery_package_type_id:
            delivery_package.package_type_id = self.delivery_package_type_id
        if self.shipping_weight:
            delivery_package.shipping_weight = self.shipping_weight
        if self.height:
            delivery_package.height = self.height

    @api.depends('picking_id', 'picking_id.move_ids', 'picking_id.move_ids.product_id',
                 'picking_id.move_ids.product_id.weight')
    def _compute_weight_deficit(self):
        for rec in self:
            moves_without_weight = rec.picking_id.move_ids.filtered(
                lambda m: not m.product_id.weight or m.product_id.weight <= 0
            )
            rec.weight_deficit = bool(moves_without_weight)
            rec.weight_deficit_products = ', '.join(moves_without_weight.mapped('product_id.name'))
            
            rec.no_done_products = False
            move_line_ids = rec.picking_id.move_line_ids.filtered(lambda m:
                float_compare(m.qty_done, 0.0, precision_rounding=m.product_uom_id.rounding) > 0
                and not m.result_package_id
            )
            if not move_line_ids:
                rec.no_done_products = True
                
                

    weight_deficit = fields.Boolean(
        string="Missing Product Weights",
        compute='_compute_weight_deficit',
    )

    weight_deficit_products = fields.Char(
        string="Products Without Weight",
        compute='_compute_weight_deficit',
    )
    
    no_done_products = fields.Boolean(
        string="Missing Product Weights",
        compute='_compute_weight_deficit',
    )
    
    # ~ @api.depends('delivery_package_type_id')
    # ~ def _compute_shipping_weight(self):
        # ~ for rec in self:
            # ~ move_line_ids = rec.picking_id.move_line_ids.filtered(lambda m:
                # ~ float_compare(m.qty_done, 0.0, precision_rounding=m.product_uom_id.rounding) > 0
                # ~ and not m.result_package_id
            # ~ )
            # ~ # Add package weights to shipping weight, package base weight is defined in package.type
            # ~ total_weight = rec.delivery_package_type_id.base_weight or 0.0
            # ~ for ml in move_line_ids:
                # ~ qty = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                # ~ total_weight += qty * ml.product_id.weight
            # ~ rec.shipping_weight = total_weight

    

    
    
    
