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
   # _name = 'stock.config.settings'
   # _inherit = 'stock.config.settings'
    _inherit = 'res.config.settings'
    fraktjakt_tid = fields.Char(string="Consignor id (test)",help="This is your id you got from the Fraktjakt test system, id/key and address are differenet from the production system.")
    fraktjakt_tkey = fields.Char(string='Consignor key (test)',help="This is your key you got from the Fraktjakt test system, id/key and address are differenet from the production system.")
    fraktjakt_turl = fields.Char(string='Url (test)',help="The test server usually https://api2.fraktjakt.se, id/key and address are different from the production system.")
    fraktjakt_pid = fields.Char(string="Consignor id", help="This is your id you got from the Fraktjakt production system, id/key and address are different from the test system.")
    fraktjakt_pkey = fields.Char(string='Consignor key',help="This is your key you got from the Fraktjakt production system, id/key and address are different from the test system.")
    fraktjakt_purl = fields.Char(string='Url',help="The production server usually https://api1.fraktjakt.se, id/key and address are different from the test system.")

    fraktjakt_environment = fields.Selection([('production','Production'),('test','Test')],string='Environment',help='Test or Production, these are different system with uniqe id/key and address')


    def set_fraktjakt(self):
        self.env['ir.config_parameter'].set_param('fraktjakt.tid', (self.fraktjakt_tid or '').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('fraktjakt.tkey', (self.fraktjakt_tkey or '').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('fraktjakt.turl', (self.fraktjakt_turl or 'https://api2.fraktjakt.se/%s').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('fraktjakt.pid', (self.fraktjakt_tid or '').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('fraktjakt.pkey', (self.fraktjakt_tkey or '').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('fraktjakt.purl', (self.fraktjakt_turl or 'https://api1.fraktjakt.se/%s').strip(), groups=['base.group_system'])
        self.env['ir.config_parameter'].set_param('fraktjakt.environment', (self.fraktjakt_environment or '').strip(), groups=['base.group_system'])
        


    def get_default_all(self):
        return {
            'fraktjakt_tid': self.env['ir.config_parameter'].get_param('fraktjakt.tid',default=''),
            'fraktjakt_pid': self.env['ir.config_parameter'].get_param('fraktjakt.pid',default=''),
            'fraktjakt_tkey': self.env['ir.config_parameter'].get_param('fraktjakt.tkey',default=''),
            'fraktjakt_pkey': self.env['ir.config_parameter'].get_param('fraktjakt.pkey',default=''),
            'fraktjakt_turl': self.env['ir.config_parameter'].get_param('fraktjakt.turl',default=''),
            'fraktjakt_purl': self.env['ir.config_parameter'].get_param('fraktjakt.purl',default=''),
            'fraktjakt_environment': self.env['ir.config_parameter'].get_param('fraktjakt.environment',default='test'),
        }
        
        
        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
