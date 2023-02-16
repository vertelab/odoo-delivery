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

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fraktjakt_tid = fields.Char(string="Consignor id (test)", config_parameter='fraktjakt.tid', help="This is your id you got from the Fraktjakt test system, id/key and address are differenet from the production system.")
    fraktjakt_tkey = fields.Char(string='Consignor key (test)',  config_parameter='fraktjakt.tkey', help="This is your key you got from the Fraktjakt test system, id/key and address are differenet from the production system.")
    fraktjakt_turl = fields.Char(string='Url (test)',config_parameter='fraktjakt.turl',help="The test server usually https://api2.fraktjakt.se, id/key and address are different from the production system.")
    fraktjakt_pid = fields.Char(string="Consignor id",config_parameter='fraktjakt.pid', help="This is your id you got from the Fraktjakt production system, id/key and address are different from the test system.")
    fraktjakt_pkey = fields.Char(string='Consignor key',config_parameter='fraktjakt.pkey',help="This is your key you got from the Fraktjakt production system, id/key and address are different from the test system.")
    fraktjakt_purl = fields.Char(string='Url',config_parameter='fraktjakt.purl',help="The production server usually https://api1.fraktjakt.se, id/key and address are different from the test system.")

    fraktjakt_environment = fields.Selection([('production','Production'),('test','Test')],string='Environment',config_parameter='fraktjakt.environment',default="test",help='Test or Production, these are different system with uniqe id/key and address')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
