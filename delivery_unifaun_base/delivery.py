# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import requests
from requests.auth import HTTPBasicAuth
import json

import logging
_logger = logging.getLogger(__name__)


class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    unifaun_service_code = fields.Char('Service Code')
    is_unifaun = fields.Boolean('Is Unifaun')
    
    def unifaun_send(self, method, params=None, payload=None):
        headers = {'content-type': 'application/json'}
        
        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        url = self.env['ir.config_parameter'].get_param('unifaun.url')
    
        response = requests.post(
            url + method,
            params=params,
            data=payload and json.dumps(payload) or None,
            headers=headers,
            verify=False,
            auth=HTTPBasicAuth(username, password))

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}
           

        return response.json()

    def unifaun_receive(self, method, params=None):
        headers = {'content-type': 'application/json'}
        
        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        url = self.env['ir.config_parameter'].get_param('unifaun.url')
        
        response = requests.get(
            url + method, 
            params=params,
            headers=headers, 
            verify=False, 
            auth=HTTPBasicAuth(username, password))

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}

        return response.json()



        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
