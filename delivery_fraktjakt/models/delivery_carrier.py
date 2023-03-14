# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2017 Tiny SPRL (<http://tiny.be>).
#       
#    Third party addon by Vertel AB
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

from io import BytesIO
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.service import common

import requests
from lxml import etree

import logging
_logger = logging.getLogger(__name__)

FRAKTJAKT_API_VERSION = '4.4'

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"
    
    is_fraktjakt = fields.Boolean('Is Fraktjakt')
    fraktjakt_id = fields.Char(string='Fraktjakt ID')
    fraktjakt_desc = fields.Char(string='Fraktjakt Description')
    partner_id = fields.Many2one(comodel_name='res.partner')
        
    def fraktjakt_send(self, method, payload=None):
        
        url = self.env['ir.config_parameter'].get_param('fraktjakt.turl' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.purl')
        _logger.error('get %s %s %s' % (url,method,payload))
        response = requests.get(url + '/' + method,params='xml=%s' % payload)
        _logger.error('get response %s %s %s' % (response.status_code,response.ok,response.content))

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return (response,response.status_code,response.text)
           
        record = etree.XML(response.content)
        code = record.find('code').text
        warning = record.find('warning_message').text
        error = record.find('error_message').text
        if code == '1':
            _logger.warning("Fraktjakt Warning %s" % warning)
        elif code == '2':
            _logger.error("Fraktjakt Error %s" % error)
            return (response,'2',error)

        return (response,'0',warning or 'OK')

    def init_element(self,tag):
        tree = etree.Element(tag)
        et = etree.ElementTree(tree)
        f = BytesIO()
        et.write(f, encoding='utf-8', xml_declaration=True) 
        return tree

    def init_subelement(self,element,tag):
        return etree.SubElement(element,tag)

    def add_subelement(self,element,tag,value):
        sub = etree.SubElement(element,tag)
        sub.text = str(value)
    
    def add_consignor(self,shipment):
        consignor = etree.SubElement(shipment,'consignor')
        self.add_subelement(consignor,'id',self.env['ir.config_parameter'].get_param('fraktjakt.tid' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pid'))
        self.add_subelement(consignor,'key',self.env['ir.config_parameter'].get_param('fraktjakt.tkey' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pkey'))
        self.add_subelement(consignor, 'currency', 'SEK')
        self.add_subelement(consignor,'language','sv')
        self.add_subelement(consignor,'encoding','utf-8')
        self.add_subelement(consignor,'system_name','Odoo')
        self.add_subelement(consignor, 'system_version', common.exp_version()['server_serie'])
        self.add_subelement(consignor,'module_version', self.env['ir.model.data'].xmlid_to_object('base.module_delivery_fraktjakt').installed_version)
        self.add_subelement(consignor,'api_version', FRAKTJAKT_API_VERSION)
        
    def add_address(self,element,tag,partner,residential = 1):
        adress = self.init_subelement(element,tag)

        self.add_subelement(adress,'street_address_1',partner.street or '')
        self.add_subelement(adress,'street_address_2',partner.street2 or '')
        self.add_subelement(adress,'postal_code',partner.zip or '') 
        self.add_subelement(adress,'city_name',partner.city or '')
        self.add_subelement(adress,'residential', residential)
        self.add_subelement(adress,'country_code',partner.country_id.code or 'SE')
        
    def get_url(self,method):
        id = self.env['ir.config_parameter'].get_param('fraktjakt.tid' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pid')
        key = self.env['ir.config_parameter'].get_param('fraktjakt.tkey' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pkey')
        url = self.env['ir.config_parameter'].get_param('fraktjakt.turl' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.purl')
        return '%s/%s?consignor_id=%s&consignor_key=%s' % (url,method,id,key)

# ~ # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
