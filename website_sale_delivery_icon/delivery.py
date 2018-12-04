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

from openerp import models, fields, api, _
from openerp import http
from openerp.http import request

import logging
_logger = logging.getLogger(__name__)

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    website_image = fields.Binary(string="Image")
    website_description_link = fields.Char(string="Description Link")
    
    website_description = fields.Text(string='Description for the website', translate=True) # adds translation
    name = fields.Char(string='Delivery Method', required=True, translate=True) 



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: