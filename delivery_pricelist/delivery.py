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
from odoo.osv import osv
from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
import odoo.addons.website_sale.controllers.main

import logging
_logger = logging.getLogger(__name__)

class delivery_carrier(osv.osv):
    _inherit = 'delivery.carrier'
    
    def name_get(self, cr, uid, ids, context=None):
        # name_get goes into an endless loop when we use contact.property_product_pricelist.id
        # in grid_get (name_get uses get_price, which uses grid_get, and
        # then its back to name_get). Limiting to one extra pass through here.
        if context and context.get('delivery_carrier_name_get_done'):
            result = []
            for record in self.read(cr, uid, ids, ['id', 'name'], context=context):
                result.append((record['id'], record['name']))
            return result
        context = dict(context or {})
        context['delivery_carrier_name_get_done'] = True
        return super(delivery_carrier, self).name_get(cr, uid, ids, context=context)
    
    def grid_get(self, cr, uid, ids, contact_id, context=None):
        contact = self.pool.get('res.partner').browse(cr, uid, contact_id, context=context)
        for carrier in self.browse(cr, uid, ids, context=context):
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
