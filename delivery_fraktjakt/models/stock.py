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
from lxml import etree
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

import logging

import requests

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_fraktjakt = fields.Boolean(related='carrier_id.is_fraktjakt')
    fraktjakt_shipmentid = fields.Char(string='Fraktjakt Shipment ID', copy=False)
    fraktjakt_orderid = fields.Char(string='Fraktjakt Order ID', copy=False)

    fraktjakt_arrival_time = fields.Char(string='Arrival Time')
    fraktjakt_price = fields.Float(string='Price')
    fraktjakt_agent_info = fields.Char(string='Agent info')
    fraktjakt_agent_link = fields.Char(string='Agent Link')

    confirm_url = fields.Char()
    cancel_url = fields.Char()
    fraktjakt_tracking_url = fields.Char()

    def open_website_url(self):
        if self.fraktjakt_tracking_url:
            return {
                'type': 'ir.actions.act_url',
                'name': "Shipment Tracking Page",
                'target': 'new',
                'url': self.fraktjakt_tracking_url,
            }
        else:
            return super().open_website_url()

    def fraktjakt_query(self):
        """Create a stored shipment."""

        if not self.env['ir.config_parameter'].get_param('fraktjakt.environment', None):
            raise ValidationError(_('Fraktjakt are not configured'))
        if self.carrier_tracking_ref:
            raise ValidationError(_('Transport already ordered (there is a Tracking ref)'))
        if self.fraktjakt_shipmentid:
            raise ValidationError(_('A stored shipment already exists for this order.'))

        query = self.env['fj_query'].sudo().create({
            'picking_id': self.id,
            'sender_id': self.picking_type_id.warehouse_id.partner_id.id,
            'reciever_id': self.partner_id.id,
            'pickup_date': self.date_deadline,
        })

        for pack in self.package_ids:
            self.env['fj_query.package'].sudo().create({
                'pack_id': pack.id,
                'weight': pack.weight,
                'wizard_id': query.id,
            })

        self.weight = sum(self.package_ids.mapped('weight'))

        if len(query.pack_ids) == 0:
            raise ValidationError(_('There is no packages to ship.'))
        if self.weight == 0:
            raise ValidationError(_('There is no weight to ship.'))
        if sum(query.pack_ids.mapped('volume')) == 0:
            raise ValidationError(_('There is no dimensions on packages.'))

        for move in self.move_line_ids:
            self.env['fj_query.commodity'].sudo().create({
                'move_id': move.move_id.id,
                'wizard_id': query.id,
                'name': move.product_id.display_name,
                'quantity': move.move_id.product_qty,
                'description': move.product_id.description_sale,
                'price': move.move_id.price_unit * move.move_id.product_qty,
            })

        form_tuple = self.env['ir.model.data']._xmlid_lookup('delivery_fraktjakt.fj_query_form_view')[2]

        return {
            'name': 'Fraktjakt Shipment Query',
            'type': 'ir.actions.act_window',
            'res_model': 'fj_query',
            'res_id': query.id,
            'view_id': form_tuple,
            'view_mode': 'form',
            'target': 'new',
        }

    # Redirect the user to Fraktjakt to confirm the shipment.
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
        record = etree.XML(response.content)
        code = record.find('code').text

        if len(record) and record.tag == 'result':
            if code == '0':
                # raise UserError('The shipment has been canceled.')
                self.write({'state': 'cancel'})
                message = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Cancel Shipment'),
                        'message': 'The shipment has been cancelled.',
                        'sticky': False,
                        'type': 'success',
                    }
                }
                return message
            else:
                # Handle the error
                message = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Cancel Shipment'),
                        'message': 'The shipment has already been cancelled.',
                        'sticky': False,
                        'type': 'danger',
                    }
                }
                return message


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    height = fields.Integer('Height', help="Packaging Height")


class StockQuantType(models.Model):
    _inherit = 'stock.package.type'

    fraktjakt_package_type = fields.Selection([
        ('pallet', 'Pallet'), ('half_pallet', 'Half Pallet'), ('others', 'Others')
    ], string="Package Type", default='pallet', required=True)

    @api.onchange('fraktjakt_package_type')
    def change_fraktjakt_package_type(self):
        if self.fraktjakt_package_type == 'pallet':
            self.packaging_length = 1200
            self.width = 800
        elif self.fraktjakt_package_type == 'half_pallet':
            self.packaging_length = 800
            self.width = 600



