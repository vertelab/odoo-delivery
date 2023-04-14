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
from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)


class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    def _carrier_data(self):
        # if self.my_delivery_type:
        #     self._carrier_data = '<input name="carrier_data" .../>
        # else:
        #     super(delivery_carrier, self)._carrier_data()
        pass
    carrier_data = fields.Text(compute="_carrier_data")

    @api.model
    def lookup_carrier(self, carrier_id, carrier_data, order):
        pass


class website_carrier_data(http.Controller):

    @http.route(['/shop/delivery/carrier_data'], type='json', auth="public", website=True)
    def lookup_carrier(self, carrier_id, carrier_data, **post):
        order = request.website.sale_get_order()
        _logger.warning('delivery-data %s %s %s' % (carrier_id, carrier_data, order))
        return request.env['delivery.carrier'].lookup_carrier(carrier_id, carrier_data, order)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
