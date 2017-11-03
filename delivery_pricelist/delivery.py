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

import openerp.exceptions
from openerp import models, fields, api, _
from openerp import http
from openerp.http import request
import openerp.addons.website_sale.controllers.main

import logging
_logger = logging.getLogger(__name__)



class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"
    @api.multi
    def grid_get(self,contact_id):
        contact = self.env['res.partner'].browse(contact_id)
        for carrier in self:
            res = super(delivery_carrier,carrier).grid_get(contact_id)
            if res:
                for grid in carrier.grids_id:
                    get_id = lambda x: x.id
                    pricelist_ids = map(get_id, grid.pricelist_ids)
                    if pricelist_ids and not contact.property_product_pricelist.id in pricelist_ids:
                        continue
                    _logger.warn('%s %s' % (grid,pricelist_ids))
                    return grid.id
        return False

class delivery_grid(models.Model):
    _inherit = "delivery.grid"

    pricelist_ids = fields.Many2many(comodel_name="product.pricelist",string="Pricelists",help="Delivery options for customers that have these pricelists.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
