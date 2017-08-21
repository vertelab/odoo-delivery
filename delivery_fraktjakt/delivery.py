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
    
    
    #~ unifaun_service_code = fields.Char('Service Code')
    is_fraktjakt = fields.Boolean('Is Fraktjakt')
    fraktjakt_id = fields.Char(string='Fraktjakt ID')
    fraktjakt_desc = fields.Char(string='Fraktjakt Description')
    
    
    def fraktjakt_send(self, method, payload=None):
        
        fraktjakt_id = self.env['ir.config_parameter'].get_param('fraktjakt.id')
        fraktjakt_key = self.env['ir.config_parameter'].get_param('fraktjakt.key')
        fraktjakt_environment = self.env['ir.config_parameter'].get_param('fraktjakt.environment')
    
        payload.format(id=fraktjakt_id,key=fraktjakt(
            fraktjakt_environment % method,
            params=params,
            data=payload and json.dumps(payload) or None,
        )

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}
           

        return response.json()

class res_partner(models.Model):
    _inherit = "res.partner"
    
    fraktjakt_id = fields.Char(string='Fraktjakt ID')

        

class stock_picking(models.Model):
    _inherit="stock.picking"
    
    is_fraktjakt = fields.Boolean(related='carrier_id.is_fraktjakt')
    fraktjakt_shipmentid = fields.Char(string='Fraktjakt Shipment ID', copy=False)
    fraktjakt_stored_shipmentid = fields.Char(string='Fraktjakt Stored Shipment ID', copy=False)
    
    
    fraktjakt_arrival_time = fields.Char(string='Arrival Time')
    fraktjakt_price = fields.Float(string='Price')
    fraktjakt_tax = fields.Many2one(comodel_name='account.tax')
    fraktjakt_agent_info = fields.Char(string='Agent info')
    fraktjakt_agent_link = fields.Char(string='Agent Link')
            
    @api.one
    def fraktjakt_order_stored_shipment(self):
        """Create a stored shipment."""
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        if self.fraktjakt_stored_shipmentid:
            raise Warning(_('A stored shipment already exists for this order.'))
        
              #~ <?xml version="1.0" encoding="UTF-8"?>
        #~ <shipment >
          #~ <value>199.50</value>
          #~ <shipper_info>1</shipper_info>
          #~ <consignor>
            #~ <id>14602</id>
            #~ <key>72b2521f735f6ffd146774e0f69f701e9e1c87ce</key>
            #~ <currency>SEK</currency>
            #~ <language>sv</language>
            #~ <encoding>UTF-8</encoding>
          #~ </consignor>
          #~ <parcels>
            #~ <parcel>
              #~ <weight>2.8</weight>
              #~ <length>30</length>
              #~ <width>20</width>
              #~ <height>10</height>
            #~ </parcel>
          #~ </parcels>
          #~ <address_to>
            #~ <street_address_1>Hedenstorp 10</street_address_1>
            #~ <street_address_2></street_address_2>
            #~ <postal_code>33292</postal_code>
            #~ <city_name>Gislaved</city_name>
            #~ <residential>1</residential>
            #~ <country_code>SE</country_code>
          #~ </address_to>
        #~ </shipment>  

        if self.picking_type_id.code == 'incoming':
            receiver = self.picking_type_id.warehouse_id.partner_id
            sender = self.partner_id
        elif self.picking_type_id.code == 'outgoing':
            sender = self.picking_type_id.warehouse_id.partner_id
            receiver = self.partner_id
        receiver_contact = sender_contact = None
        if receiver.parent_id and receiver.type == 'contact':
            receiver_contact = receiver
            receiver = self.env['res.partner'].browse(receiver.parent_id.address_get(['delivery'])['delivery'])
        if sender.parent_id and sender.type == 'contact':
            sender_contact = sender
            sender = self.env['res.partner'].browse(sender.parent_id.address_get(['delivery'])['delivery'])




        shipment = etree.Element('shipment')
        value = etree.SubElement(shipment,'value')
        value.text = 199.50
        shipper_info = etree.SubElement(shipment,'shipper_info')
        shipper_info.text = 1
        # Consignor
        consignor = etree.SubElement(shipment,'consignor')
        id = etree.SubElement(consignor,'id')
        id.text = '{id}'
        key = etree.SubElement(consignor,'key')
        key.text = '{key}'
        language = etree.SubElement(consignor,'language')
        language.text = 'sv'
        encoding = etree.SubElement(consignor,'encoding')
        encoding.text = 'UTF-8'
        # Parcels
        parcels = SubElement(shipment,'parcels')
        parcel = SubElement(parcels,'parcel')
        weight = SubElement(parcel,'weight')
        weight.text = 2.8
        length = SubElement(parcel,'length')
        length.text = 30
        width = SubElement(parcel,'width')
        width.text = 20
        height = SubElement(parcel,'height')
        height.text = 10
        # address_to
        address_to = SubElement(shipment,'address_to')
        street_address_1 = SubElement(address_to,'street_address_1')
        street_address_1.text = receiver.street
        street_address_2 = SubElement(address_to,'street_address_2')
        street_address_2.text = receiver.street2
        postal_code = SubElement(address_to,'postal_code')
        postal_code.text = receiver.zip
        city_name = SubElement(address_to,'city_name')
        city_name.text = receiver.city
        recidential = SubElement(address_to,'recidential')
        recidential.text = '1'
        country_code = SubElement(address_to,'country_code')
        country_code = receiver.country_id.code
        
        response = self.carrier_id.fraktjakt_send('fraktjakt/query_xml',etree.dump(shipment))
        
        if response.ok:
            fj = etree.xml(response.content)
            shipping_products = fj.find('shipping_products')
            for shipping_product in fj.find('shipping_products').findall('shipping_product'):
                id = shipping_product.find('id').text
                name = shipping_product.find('name').text
                desc = shipping_product.find('description').text
                arrival_time = shipping_product.find('arrival_time').text
                price = shipping_product.find('price').text
                tax_class = shipping_product.find('tax_class').text
                agent_info = shipping_product.find('agent_info').text
                agent_link = shipping_product.find('agent_link').text
                shipper = shipping_product.find('shipper')
                shipper_id = shipper.find('id').text
                shipper_name = shipper.find('name').text
                shipper_logo = shipper.find('logo_url').text
            
        #~ if type(response) == type({}):
            #~ _logger.warn('\n%s\n' % response)
            
            #~ self.unifaun_stored_shipmentid = response.get('id', '')
            
            #~ self.env['mail.message'].create({
                #~ 'body': _(u"Fraktjakt<br/>rec %s<br/>resp %s<br/>" % (etree.dump(shipment), responser
                #~ )),
                #~ 'subject': "Order Transport",
                #~ 'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,re
                #~ 'res_id': self.id,
                #~ 'model': self._name,
                #~ 'type': 'notification',
            #~ })
        #~ else:
            #~ self.env['mail.message'].create({
                #~ 'body': _("Fraktjakt error!<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                #~ 'subject': "Order Transport",
                #~ 'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                #~ 'res_id': self.id,
                #~ 'model': self._name,
                #~ 'type': 'notification',
            #~ })
        #~ _logger.warn('Fraktjakt Order Transport: rec %s response %s' % (rec,response))
    
class fj_query(models.TransientModel):
    _name = 'fj_query.import'

    picking_id = fields.Many2one(comodel_name='stock.picking',string='Picking',)
    line_ids = fields.One2many(string='Shipping products', comodel_name='mrp.to.bom.import.line', inverse_name='wizard_id')
    
    @api.one
    def fraktjakt_query(self):
        """Create a stored shipment."""
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        if self.fraktjakt_stored_shipmentid:
            raise Warning(_('A stored shipment already exists for this order.'))
        
              #~ <?xml version="1.0" encoding="UTF-8"?>
        #~ <shipment >
          #~ <value>199.50</value>
          #~ <shipper_info>1</shipper_info>
          #~ <consignor>
            #~ <id>14602</id>
            #~ <key>72b2521f735f6ffd146774e0f69f701e9e1c87ce</key>
            #~ <currency>SEK</currency>
            #~ <language>sv</language>
            #~ <encoding>UTF-8</encoding>
          #~ </consignor>
          #~ <parcels>
            #~ <parcel>
              #~ <weight>2.8</weight>
              #~ <length>30</length>
              #~ <width>20</width>
              #~ <height>10</height>
            #~ </parcel>
          #~ </parcels>
          #~ <address_to>
            #~ <street_address_1>Hedenstorp 10</street_address_1>
            #~ <street_address_2></street_address_2>
            #~ <postal_code>33292</postal_code>
            #~ <city_name>Gislaved</city_name>
            #~ <residential>1</residential>
            #~ <country_code>SE</country_code>
          #~ </address_to>
        #~ </shipment>  

        if self.picking_type_id.code == 'incoming':
            receiver = self.picking_type_id.warehouse_id.partner_id
            sender = self.partner_id
        elif self.picking_type_id.code == 'outgoing':
            sender = self.picking_type_id.warehouse_id.partner_id
            receiver = self.partner_id
        receiver_contact = sender_contact = None
        if receiver.parent_id and receiver.type == 'contact':
            receiver_contact = receiver
            receiver = self.env['res.partner'].browse(receiver.parent_id.address_get(['delivery'])['delivery'])
        if sender.parent_id and sender.type == 'contact':
            sender_contact = sender
            sender = self.env['res.partner'].browse(sender.parent_id.address_get(['delivery'])['delivery'])




        shipment = etree.Element('shipment')
        value = etree.SubElement(shipment,'value')
        value.text = 199.50
        shipper_info = etree.SubElement(shipment,'shipper_info')
        shipper_info.text = 1
        # Consignor
        consignor = etree.SubElement(shipment,'consignor')
        id = etree.SubElement(consignor,'id')
        id.text = '{id}'
        key = etree.SubElement(consignor,'key')
        key.text = '{key}'
        language = etree.SubElement(consignor,'language')
        language.text = 'sv'
        encoding = etree.SubElement(consignor,'encoding')
        encoding.text = 'UTF-8'
        # Parcels
        parcels = SubElement(shipment,'parcels')
        parcel = SubElement(parcels,'parcel')
        weight = SubElement(parcel,'weight')
        weight.text = 2.8
        length = SubElement(parcel,'length')
        length.text = 30
        width = SubElement(parcel,'width')
        width.text = 20
        height = SubElement(parcel,'height')
        height.text = 10
        # address_to
        address_to = SubElement(shipment,'address_to')
        street_address_1 = SubElement(address_to,'street_address_1')
        street_address_1.text = receiver.street
        street_address_2 = SubElement(address_to,'street_address_2')
        street_address_2.text = receiver.street2
        postal_code = SubElement(address_to,'postal_code')
        postal_code.text = receiver.zip
        city_name = SubElement(address_to,'city_name')
        city_name.text = receiver.city
        recidential = SubElement(address_to,'recidential')
        recidential.text = '1'
        country_code = SubElement(address_to,'country_code')
        country_code = receiver.country_id.code
        
        response = self.carrier_id.fraktjakt_send('fraktjakt/query_xml',etree.dump(shipment))
        
        if response.ok:
            fj = etree.xml(response.content)
            shipping_products = fj.find('shipping_products')
            for shipping_product in fj.find('shipping_products').findall('shipping_product'):
                id = shipping_product.find('id').text
                carrier = self.env['delivery.carrier'].search([('fraktjakt_id','=',shipping_product.find('id').text)])
                if not carrier:
                    res_model, product_id = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt','fraktjakt_product')
                    partner_id = None
                    partner = self.env['res.partner'].search([('fraktjakt_id','=',shipper.find('id').text)])
                    if partner:
                        partner_id = partner.id
                    if not partner_id:
                        image = None
                        if shipper.find('logo_url').text:
                            image = requets.get(shipper.find('logo_url').text).content.encode('base-64')
                        parter = self.env['res.partner'].create({
                            'fraktjakt_id': shipper.find('id').text,
                            'customer': False,
                            'supplier': True,
                            'is_company': True,
                            'name': shipper.find('name').text,
                            'image': image,
                        })
                        partner_id = partner.id
                    #~ else:
                        #~ res_model, partner_id = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt','fraktjakt_partner')
                    
                    carrier = self.env['delivery.carrier'].create({
                        'fraktjakt_id': shipping_product.find('id').text,
                        'fraktjakt_desc': shipping_product.find('description').text,
                        'is_fraktjakt': True,
                        'normal_price': shipping_product.find('price').text,
                        'product_id': product_id,
                        'partner_id': partner_id,
                        'name': shipping_product.find('name').text,
                    })
                self.line_ids |= self.env['fj.shipping_product'].create({
                   'carrier_id':  carrier.id,
                    'name': carrier.name,
                    'desc': carrier.fraktjakt_desc,
                    'arrival_time': shipping_product.find('arrival_time').text,
                    'price': shipping_product.find('price').text,
                    'agent_info': shipping_product.find('agent_info').text,
                    'agent_link': shipping_product.find('agent_link').text,
                    'shipper': carrier.partner_id.id, 
                })
                
            
        #~ if type(response) == type({}):
            #~ _logger.warn('\n%s\n' % response)
            
            #~ self.unifaun_stored_shipmentid = response.get('id', '')
            
            #~ self.env['mail.message'].create({
                #~ 'body': _(u"Fraktjakt<br/>rec %s<br/>resp %s<br/>" % (etree.dump(shipment), responser
                #~ )),
                #~ 'subject': "Order Transport",
                #~ 'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,re
                #~ 'res_id': self.id,
                #~ 'model': self._name,
                #~ 'type': 'notification',
            #~ })
        #~ else:
            #~ self.env['mail.message'].create({
                #~ 'body': _("Fraktjakt error!<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                #~ 'subject': "Order Transport",
                #~ 'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                #~ 'res_id': self.id,
                #~ 'model': self._name,
                #~ 'type': 'notification',
            #~ })
        #~ _logger.warn('Fraktjakt Order Transport: rec %s response %s' % (rec,response))
  
    @api.multi
    def import_file(self):
        if self.line_ids:
            pass


class fj_shipping_product(models.TransientModel):
    _name = 'fj.shipping_product'

    carrier_id = fields.Many2one(comodel_name='delivery.carrier')
    name = fields.Char(string="name")
    desc = fields.Char(string="Description")
    
    arrival_time = fields.Char(string='Arrival Time')
    price = fields.Float(string='Price')
#    tax_class = 
    agent_info = fields.Char(string='Agent info')
#    agent_link = shipping_product.find('agent_link').text
    shipper = fields.Many2one(comodel_name='res.partner')
    #~ shipper_id = shipper.find('id').text
    #~ shipper_name = shipper.find('name').text
    #~ shipper_logo = shipper.find('logo_url').text

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
