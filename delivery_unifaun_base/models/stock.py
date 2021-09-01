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

import logging
_logger = logging.getLogger(__name__)

# Unifaunobjekt knutna till picking_id
#stock.picking.unifaun.status
#stock.picking.unifaun.param
#stock.picking.unifaun.pdf

class stock_picking_unifaun_status(models.Model):
    _inherit = 'stock.picking.unifaun.status'

    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order')
    # unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order' required=True, ondelete='cascade')
    picking_id = fields.Many2one(required=False, ondelete=None)

class StockPickingUnifaunParam(models.Model):
    _inherit = 'stock.picking.unifaun.param'

    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order')
    # unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order' required=True, ondelete='cascade')
    picking_id = fields.Many2one(required=False, ondelete=None)

class StockPickingUnifuanPdf(models.Model):
    _inherit = 'stock.picking.unifaun.pdf'

    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order')
    # unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order', required=True, ondelete='cascade')
    picking_id = fields.Many2one(required=False, ondelete=None)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    number_of_packages = fields.Integer(string="Number of Packages")

    unifaun_id = fields.Many2one(comodel_name='unifaun.order', string='Unifaun Order', copy=False)
    unifaun_state = fields.Selection(related='unifaun_id.state')
    unifaun_own_package = fields.Boolean(string='Own Package', help="Unifaun should treat any non-packaged lines in this picking as belonging to their own unique package")

    def create_unifaun_order(self):
        _logger.warning(f'VICTOR CREATE_UNIFAUN_ORDER QUANT PACKAGES: {self.package_ids=}')
        _logger.warning(f'VICTOR CREATE_UNIFAUN_ORDER QUANT BARCODE PACKAGES: {self.barcode_package_ids=}')
        if self.unifaun_id:
            pickings = self.unifaun_id.picking_ids
        else:
            pickings = self
        pickings.unifaun_check_if_ready()
        order = self.env['unifaun.order'].create_from_pickings(pickings)
        action = self.env['ir.actions.act_window']._for_xml_id('delivery_unifaun_base.action_unifaun_order')
        action['domain'] = [('id', '=', order.id)]
        return action
    
    def unifaun_check_if_ready(self):
        """Check if this picking is ready to be sent as Unifaun Order"""
        for picking in self:
            if picking.state != 'done':
                raise Warning("Picking must be done before sending as unifaun order.")
            if not picking.is_unifaun:
                raise Warning("Carrier is not a Unifaun partner.")

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def unifaun_package_line_values(self):
        """Return a value dict for a unifaun.package.line"""
        self.ensure_one()
        values = {
            'product_id': self.product_id.id,
            'uom_id': self.product_uom_id.id,
            'qty': self.product_qty,
        }
        return values

class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    def unifaun_package_values(self):
        """Return a value dict for a unifaun.package"""
        _logger.warning(f"set weight_spec to quant.package wieght: {self.shipping_weight or self.weight}")
        _logger.warning(f"shipping weight: {self.shipping_weight}, weight: {self.weight}")
        return {
            'name': self.name,
            'quant_package_id': self.id,
            #'contents': '',
            'weight_spec': self.shipping_weight or self.weight, # Fix weight to package weight
            'packaging_id': self.packaging_id and self.packaging_id.id or None,
            'line_ids': [],
            # TODO: Add volume, length, width, height
        }
