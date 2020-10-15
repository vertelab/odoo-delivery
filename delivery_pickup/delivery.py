# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2017- Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import odoo.exceptions
from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
import odoo.addons.website_sale.controllers.main

import logging
_logger = logging.getLogger(__name__)

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    pickup_location = fields.Boolean(string="Pickup Location",help="Check this field if the Carrier Type is a pickup location for deliveries.")
    @api.one
    def _carrier_data(self):
        if self.pickup_location:
            self.carrier_data = _('<select name="carrier_data" class="selectpicker form-control carrier_select" data-style="btn-primary"><option value="1">Choose location</option>%s</select>') % \
                              '\n'.join(['<option value="%s">%s</option>' % (p.id,p.name) for p in self.env['res.partner'].search([('pickup_location','=',True)])])
        else:
            super(delivery_carrier, self)._carrier_data()

    @api.model
    def lookup_carrier(self, carrier_id, carrier_data, order):
        carrier = self.env['delivery.carrier'].browse(int(carrier_id))
        if carrier and carrier.pickup_location:
            if not carrier_data == '1':
                location = self.env['res.partner'].sudo().browse(int(carrier_data or 1))
                assert location.pickup_location == True
                order.partner_shipping_id = location.id
        else:
            super(delivery_carrier, self).lookup_carrier(carrier_id, carrier_data, order)

class ResPartner(models.Model):
    """Add some fields related to pickup locations"""
    _inherit = "res.partner"

    pickup_location = fields.Boolean(string="Pickup Location",help="Check this field if the partner is a pickup location for deliveries.")

    @api.onchange('pickup_location')
    def onchange_pickup_location(self):
        if self.pickup_location:
            self.supplier = True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
