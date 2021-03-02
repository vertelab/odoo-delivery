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

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class delivery_carrier(models.Model):
    _inherit = 'delivery.carrier'

    def name_get(self):
        # name_get goes into an endless loop when we use contact.property_product_pricelist.id
        # in grid_get (name_get uses get_price, which uses grid_get, and
        # then its back to name_get). Limiting to one extra pass through here.
        if self._context and self._context.get('delivery_carrier_name_get_done'):
            result = []
            for carrier in self:
                result.append((carrier.id, carrier.name))
            return result
        return super(delivery_carrier, self).with_context({'delivery_carrier_name_get_done': True}).name_get()

    def grid_get(self, contact_id):
        contact = self.env['res.partner'].browse(contact_id)
        for carrier in self:
            for grid in carrier.grids_id:
                get_id = lambda x: x.id
                country_ids = map(get_id, grid.country_ids)
                state_ids = map(get_id, grid.state_ids)
                pricelist_ids = map(get_id, grid.pricelist_ids)
                if country_ids and not contact.country_id.id in country_ids:
                    continue
                if state_ids and not contact.state_id.id in state_ids:
                    continue
                if grid.zip_from and (contact.zip or '')< grid.zip_from:
                    continue
                if grid.zip_to and (contact.zip or '')> grid.zip_to:
                    continue
                if grid.pricelist_ids and contact.property_product_pricelist.id not in pricelist_ids:
                    continue
                return grid.id
        return False

class delivery_grid(models.Model):
    _inherit = 'delivery.grid'

    pricelist_ids = fields.Many2many(comodel_name="product.pricelist",string="Pricelists",help="Delivery options for customers that have these pricelists.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
