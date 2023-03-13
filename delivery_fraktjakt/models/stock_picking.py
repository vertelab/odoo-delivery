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

from odoo import models, fields, api, _
from odoo.exceptions import Warning

import logging

import requests
_logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit="stock.picking"
    
    is_fraktjakt = fields.Boolean(related='carrier_id.is_fraktjakt')
    fraktjakt_shipmentid = fields.Char(string='Fraktjakt Shipment ID', copy=False)
    fraktjakt_orderid = fields.Char(string='Fraktjakt Order ID', copy=False)
    
    fraktjakt_arrival_time = fields.Char(string = 'Arrival Time')
    fraktjakt_price = fields.Float(string ='Price')
    #~ fraktjakt_tax = fields.Many2one(comodel_name='account.tax')
    fraktjakt_agent_info = fields.Char(string = 'Agent info')
    fraktjakt_agent_link = fields.Char(string = 'Agent Link')

    confirm_url = fields.Char()
    cancel_url = fields.Char()

            
    def fraktjakt_query(self):
        """Create a stored shipment."""
       
        if not self.env['ir.config_parameter'].get_param('fraktjakt.environment', None):
            raise Warning(_('Fraktjakt are not configureds'))        
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        if self.fraktjakt_shipmentid:
            raise Warning(_('A stored shipment already exists for this order.'))
        
        query = self.env['fj_query'].sudo().create({
            'picking_id': self.id,
            'sender_id': self.picking_type_id.warehouse_id.partner_id.id,
            'reciever_id': self.partner_id.id,
            #'pickup_date': self.min_date, #MiC error date_deadline
            'pickup_date': self.date_deadline,

            #~ 'move_line': None,
        })
        
        for pack in self.package_ids:
            self.env['fj_query.package'].sudo().create({
                'pack_id': pack.id,
                'weight': pack.weight,
                'wizard_id': query.id,
            })
        self.weight = sum(self.package_ids.mapped('weight'))
        if len(query.pack_ids) == 0:
            raise Warning(_('There is no packages to ship.'))
        if self.weight == 0:
            raise Warning(_('There is no weight to ship.'))
        if sum(query.pack_ids.mapped('volume')) == 0:
            raise Warning(_('There is no dimensions on packages.'))
        
            
        for move in self.move_lines:
            self.env['fj_query.commodity'].sudo().create({
                'move_id': move.id,
                'wizard_id': query.id,
                'name': move.product_id.display_name,
                'quantity': move.product_qty,
                'description': move.product_id.description_sale,
                'price': move.price_unit * move.product_qty,
                })


        form_tuple = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')
        
        return {
            'name': 'Fraktjakt Shipment Query',
            'type': 'ir.actions.act_window',
            'res_model': 'fj_query',
            'res_id': query.id,
            'view_id': form_tuple[1],
            'view_mode': 'form',
            'target': 'new',
        }
    
    def fj_confirm_shipment(self):
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': self.confirm_url,
        }
    
    # def fj_cancel_shipment(self):
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'target': 'new',
    #         'url': self.cancel_url,
    #     }

    def fj_cancel_shipment(self):
        response = requests.get(self.cancel_url, params={'param1': 'value1', 'param2': 'value2'})
        if response.text == 'ok0':
            # Show an alert in Odoo
            return {
                'type': 'ir.actions.client',
                'tag': 'dialog',
                'params': {
                    'title': 'Success',
                    'text': 'The shipment has been canceled.',
                    'buttons': [{'text': 'Ok', 'close': True}],
                    'size': 'medium'
                },
            }
        else:
            # Handle the error
            return {
                'type': 'ir.actions.client',
                'tag': 'dialog',
                'params': {
                    'title': 'Error',
                    'text': 'Failed to cancel the shipment.',
                    'buttons': [{'text': 'Ok', 'close': True}],
                    'size': 'medium'
                },
            }

        
        
class stock_quant_package(models.Model):
    _inherit = 'stock.quant.package'
    
    # ~ def _weight(self):
        # ~ self.weight = self.ul_id.weight + sum([l.qty * l.product_id.weight for l in self.quant_ids])
    # ~ weight = fields.Float(compute='_weight')
    

