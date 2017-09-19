# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, Open Source Enterprise Management Solution, third party addon
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

from openerp import models, fields, api, _
from openerp import http
from openerp.http import request

import logging
_logger = logging.getLogger(__name__)

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    website_fiscal_position = fields.Many2one(comodel_name='account.fiscal.position')

    def check_fiscal_position(self,order):
        fp = order.partner_id.property_account_position if order.partner_id.is_company else order.partner_id.parent_id.property_account_position
        _logger.warn('%s Fiscal Position Partner %s carrier %s' % (self.name,fp and fp.name,self.website_fiscal_position and self.website_fiscal_position.name))
        if fp and self.website_fiscal_position:
            return self.website_fiscal_position.id == fp.id
        elif fp:
            return False # Partner has fp hide delivery
        else:
            return True # Partner does not have fp show all 

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: