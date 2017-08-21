# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

from openerp import models, fields, api, _
from openerp.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)



class stock_config_settings(models.TransientModel):
    _name = 'stock.config.settings'
    _inherit = 'stock.config.settings'

    #~ username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
    #~ password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
    #~ url = self.env['ir.config_parameter'].get_param('unifaun.url')

    unifaun_apikey = fields.Char(string="API-key")
    unifaun_password = fields.Char(string='Password')
    unifaun_url = fields.Char(string='URL')
    unifaun_environment = fields.Selection([('production','Production'),('test','Test')],string='Environment',help='Test or Production')

    @api.one
    def set_unifaun(self):
        self.env['ir.config_parameter'].set_param('unifaun.api_key', (self.unifaun_apikey or '').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('unifaun.passwd', (self.unifaun_password or '').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('unifaun.url', (self.unifaun_url or '').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('unifaun.environment', (self.unifaun_environment or '').strip(), groups=['base.group_system'])
        

    @api.multi
    def get_default_all(self):
        return {
            'unifaun_apikey': self.env['ir.config_parameter'].get_param('unifaun.api_key',default=''),
            'unifaun_password': self.env['ir.config_parameter'].get_param('unifaun.passwd',default=''),
            'unifaun_url': self.env['ir.config_parameter'].get_param('unifaun.url',default='https://api.unifaun.com/rs-extapi/v1'),
            'unifaun_environment': self.env['ir.config_parameter'].get_param('unifaun.environment',default='test'),
        }
        
        
        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
