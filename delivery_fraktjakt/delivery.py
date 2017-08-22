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
from lxml import etree
import urllib

import logging
_logger = logging.getLogger(__name__)


class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"
    
    
    #~ unifaun_service_code = fields.Char('Service Code')
    is_fraktjakt = fields.Boolean('Is Fraktjakt')
    fraktjakt_id = fields.Char(string='Fraktjakt ID')
    fraktjakt_desc = fields.Char(string='Fraktjakt Description')
    
    
    def fraktjakt_send(self, method, payload=None):
        
        url = self.env['ir.config_parameter'].get_param('fraktjakt.turl' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.purl')
        _logger.error('get %s %s %s' % (url,method,payload))
        response = requests.get(url + '/' + method,params='xml=%s' % payload)
        _logger.error('get response %s %s %s' % (response.status_code,response.ok,response.content))

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}
           
        record = etree.XML(response.content)
        shipment = record.find('shipment')
        if shipment:
            code = shipment.find('code').text
            warning = shipment.find('warning_message').text
            error = shipment.find('error_message').text
            if code == '1':
                _logger.warning("Fraktjakt Warning %s" % warning)
            elif code == '2':
                _logger.error("Fraktjakt Error %s" % error)
                return {'status_code': response.status_code,'text': error,'response': response}

        return response
        #~ return {'status_code': response.status_code,'text': response.text,'response': response}
        

    def init_element(self,tag):
        return etree.Element(tag)

    def init_subelement(self,element,tag):
        return etree.SubElement(element,tag)

    def add_subelement(self,element,tag,value):
        sub = etree.SubElement(element,tag)
        sub.text = value


    
    def init_shipment(self,value='0.0', shipper_info='1'):
        shipment = etree.Element('shipment')
        shipment_value = etree.SubElement(shipment,'value')
        shipment_value.text = value
        shipment_shipper_info = etree.SubElement(shipment,'shipper_info')
        shipment_shipper_info.text = shipper_info
        return shipment
        
    def add_consignor(self,shipment):
        consignor = etree.SubElement(shipment,'consignor')
        id = etree.SubElement(consignor,'id')
        id.text = self.env['ir.config_parameter'].get_param('fraktjakt.tid' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pid')
        key = etree.SubElement(consignor,'key')
        key.text = self.env['ir.config_parameter'].get_param('fraktjakt.tkey' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pkey')
        language = etree.SubElement(consignor,'language')
        language.text = 'sv'
        encoding = etree.SubElement(consignor,'encoding')
        encoding.text = 'UTF-8'

    def add_subelement(self,shipment,tag,value):
        sub = etree.SubElement(shipment,tag)
        sub.text = value


    def init_parsels(self,shipment):
        return etree.SubElement(shipment,'parcels')

    def add_parcel(self,parcels):
        parcel = etree.SubElement(parcels,'parcel')
        weight = etree.SubElement(parcel,'weight')
        weight.text = '2.8'
        length = etree.SubElement(parcel,'length')
        length.text = '30'
        width = etree.SubElement(parcel,'width')
        width.text = '20'
        height = etree.SubElement(parcel,'height')
        height.text = '10'
        
    def add_address_to(self,shipment,partner):
        address_to = etree.SubElement(shipment,'address_to')
        street_address_1 = etree.SubElement(address_to,'street_address_1')
        street_address_1.text = partner.street
        street_address_2 = etree.SubElement(address_to,'street_address_2')
        street_address_2.text = partner.street2 if partner.street2 else '' 
        postal_code = etree.SubElement(address_to,'postal_code')
        postal_code.text = partner.zip
        city_name = etree.SubElement(address_to,'city_name')
        city_name.text = partner.city
        recidential = etree.SubElement(address_to,'recidential')
        recidential.text = '1'
        country_code = etree.SubElement(address_to,'country_code')
        country_code.text = partner.country_id.code or 'SE'

    def add_address_from(self,shipment,partner):
        address_from = etree.SubElement(shipment,'address_from')
        street_address_1 = etree.SubElement(address_from,'street_address_1')
        street_address_1.text = partner.street
        street_address_2 = etree.SubElement(address_from,'street_address_2')
        street_address_2.text = partner.street2 if partner.street2 else ''
        postal_code = etree.SubElement(address_from,'postal_code')
        postal_code.text = partner.zip
        city_name = etree.SubElement(address_from,'city_name')
        city_name.text = partner.city
        recidential = etree.SubElement(address_from,'recidential')
        recidential.text = '1'
        country_code = etree.SubElement(address_from,'country_code')
        country_code.text = partner.country_id.code or 'SE'
    


class res_partner(models.Model):
    _inherit = "res.partner"
    
    fraktjakt_id = fields.Char(string='Fraktjakt ID')

        

class stock_picking(models.Model):
    _inherit="stock.picking"
    
    is_fraktjakt = fields.Boolean(related='carrier_id.is_fraktjakt')
    fraktjakt_shipmentid = fields.Char(string='Fraktjakt Shipment ID', copy=False)
    fraktjakt_orderid = fields.Char(string='Fraktjakt Order ID', copy=False)
    
    
    fraktjakt_arrival_time = fields.Char(string='Arrival Time')
    fraktjakt_price = fields.Float(string='Price')
    #~ fraktjakt_tax = fields.Many2one(comodel_name='account.tax')
    fraktjakt_agent_info = fields.Char(string='Agent info')
    fraktjakt_agent_link = fields.Char(string='Agent Link')
            
    @api.multi
    def fraktjakt_query(self):
        """Create a stored shipment."""
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        if self.fraktjakt_shipmentid:
            raise Warning(_('A stored shipment already exists for this order.'))
        query = self.env['fj_query'].create({
            'picking_id': self.id,
            'sender_id': self.picking_type_id.warehouse_id.partner_id.id,
            'reciever_id': self.partner_id.id,
            'pickup_date': self.min_date
        })


        form_tuple = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')
        
        return {
            'name': 'Shipment Query',
            'type': 'ir.actions.act_window',
            'res_model': 'fj_query',
            'res_id': query.id,
            'view_id': form_tuple[1],
            'view_mode': 'form',
            'target': 'new',
        }
        
       
    
class fj_query(models.TransientModel):
    _name = 'fj_query'

    picking_id = fields.Many2one(comodel_name='stock.picking',string='Picking',)
    line_ids = fields.One2many(string='Shipping products', comodel_name='fj_query.line', inverse_name='wizard_id')
    pack_ids = fields.One2many(string='Packages', comodel_name='stock.quant.package')
    move_lines = fields.One2many(string='Products',comodel_name='stock.move')
    sender_id = fields.Many2one(comodel_name='res.partner',string='Sender',)
    reciever_id = fields.Many2one(comodel_name='res.partner',string='Reciever',)
    cold = fields.Boolean(string='Cold',help="Cargo contains packeges that should be cold")
    freeze = fields.Boolean(string='Freeze',help="Cargo contains packeges that should hold under freezing point")
    pickup = fields.Boolean(string='Pickup',)
    express = fields.Boolean(string='Express',)
    dropoff = fields.Boolean(string='Drop off',)
    green = fields.Boolean(string='Green',)
    quality = fields.Boolean(string='Quality',)
    time_guarantee = fields.Boolean(string='Time Guarantee',)
    pickup_date = fields.Date(string='Pickup Date',)
    driving_instructions = fields.Text(string='Driving Instructions',)
    user_notes = fields.Text(string='Notes',)
    message = fields.Text()
    
    @api.multi
    def fraktjakt_query(self):
        """Create a stored shipment."""
        
        self.line_ids = None
        self.message = ''
        
        carrier = self.picking_id.carrier_id
        shipment = carrier.init_shipment()
        carrier.add_consignor(shipment)
        parcels = carrier.init_parsels(shipment)
        carrier.add_parcel(parcels)
        carrier.add_address_to(shipment,self.reciever_id)
        #~ carrier.add_address_from(shipment,self.sender_id)
        if self.cold:
            carrier.add_subelement(shipment,'cold','1')
        if self.freeze:
            carrier.add_subelement(shipment,'freeze','1')
        if self.pickup:
            carrier.add_subelement(shipment,'pickup','1')
        if self.express:
            carrier.add_subelement(shipment,'express','1')
        if self.dropoff:
            carrier.add_subelement(shipment,'dropoff','1')
        if self.green:
            carrier.add_subelement(shipment,'green','1')
        if self.quality:
            carrier.add_subelement(shipment,'quality','1')
        if self.time_guarantee:
            carrier.add_subelement(shipment,'time_guarantee','1')
        
        response = carrier.fraktjakt_send('fraktjakt/query_xml',urllib.quote_plus(etree.tostring(shipment)))
        
        
        if response.ok:
            fj = etree.XML(response.content)
            shipping_products = fj.find('shipping_products')
            for shipping_product in fj.find('shipping_products').findall('shipping_product'):
                id = shipping_product.find('id').text
                carrier = self.env['delivery.carrier'].search([('fraktjakt_id','=',shipping_product.find('id').text)])
                if not carrier:
                    res_model, product_id = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt','fraktjakt_product')
                    partner_id = None
                    shipper = shipping_product.find('shipper')
                    partner = self.env['res.partner'].search([('fraktjakt_id','=',shipper.find('id').text)])
                    if partner:
                        partner_id = partner.id
                    if not partner_id:
                        image = None
                        if shipper.find('logo_url').text:
                            image = requests.get(shipper.find('logo_url').text).content.encode('base-64')
                        parter = self.env['res.partner'].create({
                            'fraktjakt_id': shipper.find('id').text,
                            'customer': False,
                            'supplier': True,
                            'is_company': True,
                            'name': shipper.find('name').text,
                            'image': image,
                        })
                        partner_id = partner.id
                    partner = self.env['res.partner'].search([('fraktjakt_id','=',shipper.find('id').text)])
                    if partner:
                        partner_id = partner.id
                        
                    carrier = self.env['delivery.carrier'].create({
                        'fraktjakt_id': shipping_product.find('id').text,
                        'fraktjakt_desc': shipping_product.find('description').text,
                        'is_fraktjakt': True,
                        'normal_price': shipping_product.find('price').text,
                        'product_id': product_id,
                        'partner_id': partner_id,
                        'name': shipping_product.find('name').text,
                    })
                self.line_ids |= self.env['fj_query.line'].create({
                   'carrier_id':  carrier.id,
                    'name': carrier.name,
                    'desc': carrier.fraktjakt_desc,
                    'arrival_time': shipping_product.find('arrival_time').text,
                    'price': shipping_product.find('price').text,
                    'agent_info': shipping_product.find('agent_info').text,
                    'agent_link': shipping_product.find('agent_link').text,
                    'shipper': carrier.partner_id.id, 
                })
            else:
                self.message = response.content
                
            form_tuple = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')
            return {
            'name': 'Shipment Query',
            'type': 'ir.actions.act_window',
            'res_model': 'fj_query',
            'res_id': self.id,
            'view_id': form_tuple[1],
            'view_mode': 'form',
            'target': 'new',
        }


class fj_query_line(models.TransientModel):
    _name = 'fj_query.line'

    carrier_id = fields.Many2one(comodel_name='delivery.carrier')
    wizard_id = fields.Many2one(comodel_name='fj_query')
    name = fields.Char(string="name")
    desc = fields.Char(string="Description")
    
    arrival_time = fields.Char(string='Arrival Time')
    price = fields.Float(string='Price')
#    tax_class = 
    agent_info = fields.Char(string='Agent info')
    agent_link = fields.Char(string='Agent link')
    shipper = fields.Many2one(comodel_name='res.partner')
    #~ shipper_id = shipper.find('id').text
    #~ shipper_name = shipper.find('name').text
    #~ shipper_logo = shipper.find('logo_url').text
    
    @api.multi
    def choose_product(self):

        
        self.wizard_id.fraktjakt_arrival_time = self.arrival_time
        self.wizard_id.fraktjakt_price = self.price
        self.wizard_id.fraktjakt_agent_info = self.agent_info
        self.wizard_id.fraktjakt_agent_link = self.agent_link


        carrier = self.wizard_id.picking_id.carrier_id
        order = carrier.init_element('OrderSpecification')
        carrier.add_consignor(order)
        carrier.add_subelement(order,'shipping_product_id',self.carrier_id.fraktjakt_id)
        carrier.add_subelement(order,'reference',self.wizard_id.picking_id.name)
        # Comodoties
        comodities = carrier.init_subelement(order,'comodities')
        comodity = carrier.init_subelement(comodities,'comodity')
        carrier.add_subelement(comodity,'name',self.wizard_id.picking_id.name)
        carrier.add_subelement(comodity,'quantity',self.wizard_id.picking_id.name)
        carrier.add_subelement(comodity,'description',self.wizard_id.picking_id.name)
        
        # Parcels
        parcels = carrier.init_parsels(order)
        parcel = carrier.init_subelement(parcels,'parcel')
        carrier.add_subelement(parcel,'weight','2.8')
        carrier.add_subelement(parcel,'height','15')
        carrier.add_subelement(parcel,'width','20')
        carrier.add_subelement(parcel,'length','25')
        # Recipient
        recipient = carrier.init_subelement(order,'recipient')
        #~ carrier.add_subelement(recipient,'company_to',self.wizard_id.picking_id.partner_id.)
        carrier.add_subelement(recipient,'name_to',self.wizard_id.picking_id.partner_id.name)
        carrier.add_subelement(recipient,'telephone_to',self.wizard_id.picking_id.partner_id.phone or '')
        carrier.add_subelement(recipient,'mobile_to',self.wizard_id.picking_id.partner_id.mobile or '')
        carrier.add_subelement(recipient,'email_to',self.wizard_id.picking_id.partner_id.email or '')
        # Booking
        booking = carrier.init_subelement(order,'booking')
        carrier.add_subelement(booking,'pickup_date',self.wizard_id.pickup_date or '')
        carrier.add_subelement(booking,'driving_instructions',self.wizard_id.driving_instructions or '')
        carrier.add_subelement(booking,'user_notes',self.wizard_id.user_notes or '')
        carrier.add_address_to(order,self.wizard_id.reciever_id)
        #~ carrier.add_address_from(order,self.wizard_id.sender_id)
        
        
        response = carrier.fraktjakt_send('orders/order_xml',urllib.quote_plus(etree.tostring(order)))
        
        record = etree.XML(response.content)
        result = record.find('result')
        self.wizard_id.message = response.content
        if result:
            code = result.find('code').text
            warning = result.find('warning_message').text
            error = result.find('error_message').text
            self.wizard_id.picking_id.fraktjakt_shipmentid = result.find('shipment_id').text
            self.wizard_id.picking_id.fraktjakt_orderid = result.find('order_id').text            
            _logger.warn('Order response %s %s %s' % (code,warning,error))
            if code in ['1','2']:
                form_tuple = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')
                return {
                'name': 'Shipment Query',
                'type': 'ir.actions.act_window',
                'res_model': 'fj_query',
                'res_id': self.wizard_id.id,
                'view_id': form_tuple[1],
                'view_mode': 'form',
                'target': 'new',
            }
        else:        
            form_tuple = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')
            return {
            'name': 'Shipment Query',
            'type': 'ir.actions.act_window',
            'res_model': 'fj_query',
            'res_id': self.wizard_id.id,
            'view_id': form_tuple[1],
            'view_mode': 'form',
            'target': 'new',
        }
        
                
                
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
