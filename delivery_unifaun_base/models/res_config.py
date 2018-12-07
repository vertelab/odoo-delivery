# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
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

import logging
_logger = logging.getLogger(__name__)


class stock_config_settings(models.TransientModel):
    _inherit = 'stock.config.settings'

    unifaun_apikey = fields.Char(string="API-key")
    unifaun_password = fields.Char(string='Password')
    unifaun_url = fields.Char(string='URL')
    unifaun_environment = fields.Selection([('production','Production'),('test','Test')],string='Environment',help='Test or Production')

    @api.multi
    def set_unifaun(self):
        icp = self.env['ir.config_parameter']
        icp.set_param('unifaun.api_key', (self.unifaun_apikey or '').strip(), groups=['base.group_system'])
        icp.set_param('unifaun.passwd', (self.unifaun_password or '').strip(), groups=['base.group_system'])
        icp.set_param('unifaun.url', (self.unifaun_url or '').strip(), groups=['base.group_system'])
        icp.set_param('unifaun.environment', (self.unifaun_environment or '').strip(), groups=['base.group_system'])

    @api.model
    def get_default_all(self, fields=None):
        icp = self.env['ir.config_parameter']
        return {
            'unifaun_apikey': icp.get_param('unifaun.api_key', default=''),
            'unifaun_password': icp.get_param('unifaun.passwd', default=''),
            'unifaun_url': icp.get_param('unifaun.url', default='https://api.unifaun.com/rs-extapi/v1'),
            'unifaun_environment': icp.get_param('unifaun.environment', default='test'),
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
