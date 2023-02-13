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

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp

import requests
from lxml import etree
import urllib

import logging
_logger = logging.getLogger(__name__)

FRAKTJAKT_API_VERSION = '2.91'

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"
    
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
        return etree.Element(tag)

    def init_subelement(self,element,tag):
        return etree.SubElement(element,tag)

    def add_subelement(self,element,tag,value):
        sub = etree.SubElement(element,tag)
        sub.text = value
    
    def add_consignor(self,shipment):
        consignor = etree.SubElement(shipment,'consignor')
        self.add_subelement(consignor,'id',self.env['ir.config_parameter'].get_param('fraktjakt.tid' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pid'))
        self.add_subelement(consignor,'key',self.env['ir.config_parameter'].get_param('fraktjakt.tkey' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pkey'))
        self.add_subelement(consignor,'language','sv')
        self.add_subelement(consignor,'encoding','UTF-8')
        self.add_subelement(consignor,'system_name','Odoo')
        self.add_subelement(consignor,'system_version',openerp.service.common.exp_version()['server_serie'])
        self.add_subelement(consignor,'module_version',self.env['ir.model.data'].xmlid_to_object('base.module_delivery_fraktjakt').installed_version)
        self.add_subelement(consignor,'api_version',FRAKTJAKT_API_VERSION)
        
    def add_address(self,element,tag,partner):
        adress = self.init_subelement(element,tag)
        self.add_subelement(adress,'street_address_1',partner.street or '')
        self.add_subelement(adress,'street_address_2',partner.street2 or '')
        self.add_subelement(adress,'postal_code',partner.zip or '') 
        self.add_subelement(adress,'city_name',partner.city or '')
        self.add_subelement(adress,'residential','0')
        self.add_subelement(adress,'country_code',partner.country_id.code or 'SE')
        
    def get_url(self,method):
        id = self.env['ir.config_parameter'].get_param('fraktjakt.tid' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pid')
        key = self.env['ir.config_parameter'].get_param('fraktjakt.tkey' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.pkey')
        url = self.env['ir.config_parameter'].get_param('fraktjakt.turl' if self.env['ir.config_parameter'].get_param('fraktjakt.environment') == 'test' else 'fraktjakt.purl')
        return '%s/%s?consigner_id=%s&consigner_key=%s' % (url,method,id,key)


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
            
    def fraktjakt_query(self):
        pass

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
            
    def fraktjakt_query(self):
        """Create a stored shipment."""
       
        if not self.env['ir.config_parameter'].get_param('fraktjakt.environment',None):
            raise Warning(_('Fraktjakt are not configureds'))        
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        if self.fraktjakt_shipmentid:
            raise Warning(_('A stored shipment already exists for this order.'))
        




        query = self.env['fj_query'].create({
            'picking_id': self.id,
            'sender_id': self.picking_type_id.warehouse_id.partner_id.id,
            'reciever_id': self.partner_id.id,
            #'pickup_date': self.min_date, #MiC error date_deadline
            'pickup_date': self.date_deadline,

            #~ 'move_line': None,
        })
        
        for pack in set(self.pack_operation_ids.mapped('result_package_id')):
            self.env['fj_query.package'].create({
                'pack_id': pack.id,
                'weight': pack.weight,
                'wizard_id': query.id,
            })
        self.weight = sum(self.pack_operation_ids.mapped('result_package_id').mapped('weight'))
        if len(query.pack_ids) == 0:
            raise Warning(_('There is no packages to ship.'))
        if self.weight == 0:
            raise Warning(_('There is no weight to ship.'))
        if sum(query.pack_ids.mapped('volume')) == 0:
            raise Warning(_('There is no dimensions on packages.'))
        
            
        for move in self.move_lines:
            self.env['fj_query.commodity'].create({
                'move_id': move.id,
                'wizard_id': query.id,
                'name': move.product_id.display_name,
                'quantity': move.product_uos_qty,
                'description': move.product_id.description_sale,
                'price': move.price_unit * move.product_uos_qty,
                })


        form_tuple = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')
        
        return {
            'name': 'Fraktjakt Shipment Query',
            'type': 'ir.actions.act_window',
            'res_model': 'fj_query',
            'res_id': query.id,
            'view_id': form_tuple[1],
            'view_mode': 'form',
            'target': 'new',
        }
        
class stock_quant_package(models.Model):
    _inherit = 'stock.quant.package'
    
    def _weight(self):
        self.weight = self.ul_id.weight + sum([l.qty * l.product_id.weight for l in self.quant_ids])
    weight = fields.Float(compute='_weight')
    
class fj_query(models.TransientModel):
    _name = 'fj_query'

    picking_id = fields.Many2one(comodel_name='stock.picking',string='Picking',)
    # ~ line_ids = fields.One2many(string='Shipping products', comodel_name='fj_query.line', inverse_name='wizard_id')  #mic
    # ~ pack_ids = fields.One2many(string='Packages', comodel_name='fj_query.package', inverse_name='wizard_id')  #mic
    # ~ move_lines = fields.One2many(string='Products',comodel_name='fj_query.commodity',inverse_name='wizard_id')  #mic
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
    
    def fraktjakt_query(self):
        """Create a stored shipment."""
        
        self.line_ids = None
        self.message = ''
        
        carrier = self.picking_id.carrier_id
        shipment = carrier.init_element('shipment')
        carrier.add_subelement(shipment,'value',str(sum(self.move_lines.mapped('price'))))
        carrier.add_subelement(shipment,'shipper_info','1')
        carrier.add_consignor(shipment)
        parcels = carrier.init_subelement(shipment,'parcels')
        for package in self.pack_ids:
            parcel = carrier.init_subelement(parcels,'parcel')
            carrier.add_subelement(parcel,'weight',str(package.weight))
            carrier.add_subelement(parcel,'height',str(package.height))
            carrier.add_subelement(parcel,'width',str(package.width))
            carrier.add_subelement(parcel,'length',str(package.length))
        
        carrier.add_address(shipment,'address_to',self.reciever_id)
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
        _logger.warn(etree.tostring(shipment, pretty_print=True))
        response,code,self.message = carrier.fraktjakt_send('fraktjakt/query_xml',urllib.quote_plus(etree.tostring(shipment)))
        if code in ['0','1']:
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
        return {
            'name': 'Fraktjakt Shipment Query',
            'type': 'ir.actions.act_window',
            'res_model': 'fj_query',
            'res_id': self.id,
            'view_id': self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')[1],
            'view_mode': 'form',
            'target': 'new',
            }


class fj_query_line(models.TransientModel):
    _name = 'fj_query.line'

    wizard_id = fields.Many2one(comodel_name='fj_query')
    carrier_id = fields.Many2one(comodel_name='delivery.carrier')
    # ~ partner_id = fields.Many2one(related='carrier_id.partner_id')   #mic
    # ~ image = fields.Binary(related='carrier_id.partner_id.image')    #mic
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
    
    def choose_product(self):
        self.wizard_id.fraktjakt_arrival_time = self.arrival_time
        self.wizard_id.fraktjakt_price = self.price
        self.wizard_id.fraktjakt_agent_info = self.agent_info
        self.wizard_id.fraktjakt_agent_link = self.agent_link

        carrier = self.wizard_id.picking_id.carrier_id
        order = carrier.init_element('OrderSpecification')
        carrier.add_consignor(order)
        carrier.add_subelement(order,'shipping_product_id',self.carrier_id.fraktjakt_id)
        carrier.add_subelement(order,'reference', self.wizard_id.picking_id.name.replace('/', ' '))
        # Comodoties
        commodities = carrier.init_subelement(order,'commodities')
        for move in self.wizard_id.move_lines:
            commodity = carrier.init_subelement(commodities,'commodity')
            carrier.add_subelement(commodity,'name',move.name)
            carrier.add_subelement(commodity,'quantity', str(int(move.quantity)))
            carrier.add_subelement(commodity,'description',move.description or '')
 
        # Parcels
        parcels = carrier.init_subelement(order,'parcels')
        for package in self.wizard_id.pack_ids:
            parcel = carrier.init_subelement(parcels,'parcel')
            carrier.add_subelement(parcel,'weight', str(package.weight))
            carrier.add_subelement(parcel,'length', str(package.length))
            carrier.add_subelement(parcel,'width', str(package.width))
            carrier.add_subelement(parcel,'height', str(package.height))
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
        # Address 
        carrier.add_address(order,'address_to',self.wizard_id.reciever_id)
        # ~ #~ carrier.add_address_from(order,self.wizard_id.sender_id)
        
        _logger.warn(etree.tostring(order, pretty_print=True))
        response,code,self.message = carrier.fraktjakt_send('orders/order_xml',urllib.quote_plus(etree.tostring(order)))
        
        record = etree.XML(response.content)
        _logger.warn(etree.tostring(record, pretty_print=True))
        self.wizard_id.message = response.content
        if record and record.tag == 'result':
            code = record.find('code').text
            warning = record.find('warning_message').text
            error = record.find('error_message').text
            picking = self.wizard_id.picking_id
            picking.fraktjakt_shipmentid = record.find('shipment_id').text
            picking.fraktjakt_orderid = record.find('order_id').text
            picking.fraktjakt_arrival_time = self.arrival_time
            picking.fraktjakt_price = self.price
            picking.fraktjakt_agent_info = self.agent_info
            picking.fraktjakt_agent_link = self.agent_link
            picking.carrier_id = self.carrier_id
                        
            _logger.warn('Order response %s %s %s' % (code,warning,error))
            if code in ['2']:
                return {
                'name': 'Fraktjakt Shipment Query',
                'type': 'ir.actions.act_window',
                'res_model': 'fj_query',
                'res_id': self.wizard_id.id,
                'view_id': self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')[1],
                'view_mode': 'form',
                'target': 'new',
            }
            else:
               shipping_id = "Shipping ID <a href='%s'>%s</a>" % (carrier.get_url('shipments/show/%s' % picking.fraktjakt_shipmentid),picking.fraktjakt_shipmentid)
               order_id = "Order <a href='%s'>%s</a>" % (carrier.get_url('orders/show/%s' % picking.fraktjakt_orderid),picking.fraktjakt_orderid)
               payment_link = "<href='%s'>Payment</a>" % (record.find('payment_link').text) if record.find('payment_link') else '' 
               order_confirmation_link = "<href='%s'>Order confirmation</a>" % (record.find('sender_email_link').text) if record.find('sender_email_link') else ''
               
               self.env['mail.message'].create({
                    'body': _("Fraktjakt %s %s %s %s\nCode %s\n%s\n" % (shipping_id,order_id,payment_link,order_confirmation_link,code,warning or error or '')),
                    'subject': "Fraktjakt",
                    'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                    'res_id': picking.id,
                    'model': picking._name,
                    'type': 'notification',})
        else:        
            form_tuple = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')
            return {
            'name': 'Fraktjakt Shipment Query',
            'type': 'ir.actions.act_window',
            'res_model': 'fj_query',
            'res_id': self.wizard_id.id,
            'view_id': form_tuple[1],
            'view_mode': 'form',
            'target': 'new',
        }
        
class fj_query_package(models.TransientModel):
    _name = 'fj_query.package'

    wizard_id = fields.Many2one(comodel_name='fj_query')
    pack_id = fields.Many2one(string='Package', comodel_name='stock.quant.package')
    weight = fields.Float()
    # ~ height = fields.Float(related='pack_id.ul_id.height')   #mic
    # ~ width = fields.Float(related='pack_id.ul_id.width')   #mic
    # ~ length = fields.Float(related='pack_id.ul_id.length')   #mic

    def _volume(self):
        self.volume = self.height * self.width * self.length / 1000.0
    volume = fields.Float(compute='_volume')

class fj_query_commodity(models.TransientModel):
    _name = 'fj_query.commodity'

    wizard_id = fields.Many2one(comodel_name='fj_query')
    move_id = fields.Many2one(string='Product', comodel_name='stock.move')
    name = fields.Char()
    quantity = fields.Float()
    description = fields.Char()
    price = fields.Float()
                
# ~ # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
