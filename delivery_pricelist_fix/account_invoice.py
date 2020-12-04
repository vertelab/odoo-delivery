# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
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

from openerp import api, models, fields, _
import openerp.addons.decimal_precision as dp
import logging
from openerp.exceptions import Warning
_logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    @api.multi
    def _prepare_shipping_invoice_line(self,picking,invoice):
        """Prepare the invoice line to add to the shipping costs to the shipping's
           invoice.

            :param browse_record picking: the stock picking being invoiced
            :param browse_record invoice: the stock picking's invoice
            :return: dict containing the values to create the invoice line,
                     or None to create nothing
        """
        res = super(stock_picking,self)._prepare_shipping_invoice_line(picking,invoice)
        _logger.warn('%s Haze' %invoice.picking_id.sale_id.pricelist_id.id)
        if res:
            res['price_unit'] = picking.carrier_id.product_id.get_pricelist_chart_line(invoice.picking_id.sale_id.pricelist_id.id).price
            _logger.warn('Haze %s' %res['price_unit'])
        
        return res
