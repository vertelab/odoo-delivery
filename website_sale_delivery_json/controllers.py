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
import odoo
from odoo import http
from odoo.http import request
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
import logging
_logger = logging.getLogger(__name__)

class WebsiteSaleDelivery(WebsiteSaleDelivery):

    @http.route(['/shop/payment/delivery_update'], type='json', auth='public', website=True)
    def delivery_update(self, carrier_id, **kw):
        order = request.website.sale_get_order()
        if order and carrier_id:
            order.carrier_id = int(carrier_id)
            order.delivery_set()
        return {'amount_total': self.formatted_price(order.amount_total), 'amount_tax': self.formatted_price(order.amount_tax), 'amount_delivery': self.formatted_price(order.amount_delivery)}

    def formatted_price(self, price):
        lang = request.env['res.lang'].search([('code', '=', request.env.user.lang)])
        if len(lang) > 0:
            price = '%.2f' %price
            return price.replace('.', lang.decimal_point)
        return price
