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
import base64
import requests
from odoo import models, fields, api, _
from odoo.exceptions import Warning

from lxml import etree
import urllib.parse

import logging
_logger = logging.getLogger(__name__)

FRAKTJAKT_API_VERSION = '4.4'
    
class fj_query(models.TransientModel):
    _name = 'fj_query'
    _description = 'Fraktjakt Query'

    fraktjakt_price = fields.Float(string='Price')
    fraktjakt_agent_info = fields.Char(string='Agent info')
    fraktjakt_agent_link = fields.Char(string='Agent link')
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Picking',)
    line_ids = fields.One2many(string='Shipping products', comodel_name='fj_query.line', inverse_name='wizard_id')  #mic
    pack_ids = fields.One2many(string='Packages', comodel_name='fj_query.package', inverse_name='wizard_id')  #mic
    move_lines = fields.One2many(string='Products',comodel_name='fj_query.commodity',inverse_name='wizard_id')  #mic
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
    # user_notes = fields.Text(string='Notes',)
    message = fields.Text()
    fraktjakt_arrival_time = fields.Char(related="picking_id.fraktjakt_arrival_time", string='Arrival Time')
    
    def fraktjakt_query(self):
        """Create a stored shipment."""
        
        self.line_ids = None
        self.message = ''
        
        carrier = self.picking_id.carrier_id
        shipment = carrier.init_element('shipment')
        carrier.add_subelement(shipment,'value',str(sum(self.pack_ids.pack_id.quant_ids.product_id.mapped('lst_price'))))
        carrier.add_subelement(shipment,'shipper_info','1')
        carrier.add_consignor(shipment)
        cm_uom = self.env["uom.uom"].search([('name','=',"cm")])

        default_uom = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()
        

        parcels = carrier.init_subelement(shipment,'parcels')
        for package in self.pack_ids:
            package_uom = package.pack_id.packaging_id.product_uom_id
            if not package_uom:
                package_uom = default_uom
            parcel = carrier.init_subelement(parcels,'parcel')
            carrier.add_subelement(parcel,'weight',str(package.weight))
            carrier.add_subelement(parcel,'height',str(package_uom._compute_quantity(package.height,cm_uom)))
            carrier.add_subelement(parcel,'width',str(package_uom._compute_quantity(package.width,cm_uom)))
            carrier.add_subelement(parcel,'length',str(package_uom._compute_quantity(package.length,cm_uom)))
        
        if self.reciever_id.company_type == 'company':
            carrier.add_subelement(shipment, 'company_to', self.reciever_id.name)
            carrier.add_address(shipment,'address_to',self.reciever_id, 0)
        else:
            carrier.add_address(shipment,'address_to',self.reciever_id)

        carrier.add_address(shipment, 'address_from', self.sender_id, 0)
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
        response,code,self.message = carrier.fraktjakt_send('fraktjakt/query_xml', urllib.parse.quote_plus(etree.tostring(shipment, encoding='UTF-8')))
        if code in ['0','1']:
            fj = etree.XML(response.content)
            shipping_products = fj.find('shipping_products')
            for shipping_product in fj.find('shipping_products').findall('shipping_product'):
                id = shipping_product.find('id').text
                carrier = self.env['delivery.carrier'].search([('fraktjakt_id','=',shipping_product.find('id').text)])
                if not carrier:
                    res_model, product_id = self.env['ir.model.data'].get_object_reference('delivery_fraktjakt','fraktjakt_product')
                    partner_id = False
                    shipper = shipping_product.find('shipper')
                    partner = self.env['res.partner'].search([('fraktjakt_id','=',shipper.find('id').text)])
                    if partner:
                        partner_id = partner.id
                    if not partner_id:
                        image = None
                        if shipper.find('logo_url').text:
                            image = requests.get(shipper.find('logo_url').text).content
                            encoded_image = base64.b64encode(image).decode('utf-8')
                        partner = self.env['res.partner'].create({
                            'fraktjakt_id': shipper.find('id').text,
                            # 'customer': False,
                            # 'supplier': True,
                            'is_company': True,
                            'name': shipper.find('name').text,
                            'image_1920': encoded_image,
                        })
                        partner_id = partner.id
                    partner = self.env['res.partner'].search([('fraktjakt_id','=',shipper.find('id').text)])
                    carrier = self.env['delivery.carrier'].create({
                        'fraktjakt_id': shipping_product.find('id').text,
                        'fraktjakt_desc': shipping_product.find('description').text,
                        'is_fraktjakt': True,
                        'partner_id':partner.id,
                        # 'normal_price': shipping_product.find('price').text,
                        'product_id': product_id,
                        'name': shipping_product.find('name').text,
                    })
                self.line_ids |= self.env['fj_query.line'].create({
                    'partner_id': carrier.partner_id,
                    'image': carrier.partner_id.image_1920,
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
    _description = 'Fraktjakt Query Line'

    wizard_id = fields.Many2one(comodel_name='fj_query')
    carrier_id = fields.Many2one(comodel_name='delivery.carrier')
    partner_id = fields.Many2one(related='carrier_id.partner_id')
    image = fields.Binary()
    name = fields.Char(string="name")
    desc = fields.Char(string="Description")
    message = fields.Text()
    
    arrival_time = fields.Char(string='Arrival Time')
    price = fields.Float(string='Price')
    agent_info = fields.Char(string='Agent info')
    agent_link = fields.Char(string='Agent link')
    shipper = fields.Many2one(comodel_name='res.partner')
    def get_shipper_info(self):
        shipper_id = self.shipper.id
        shipper_name = self.shipper.name
        shipper_logo = self.shipper.logo_url
        return shipper_id, shipper_name, shipper_logo
    
    # Choose Carrier
    def choose_product(self):
        self.wizard_id.fraktjakt_arrival_time = self.arrival_time
        self.wizard_id.fraktjakt_price = self.price
        self.wizard_id.fraktjakt_agent_info = self.agent_info
        self.wizard_id.fraktjakt_agent_link = self.agent_link

        # Target sending company VAT
        company_vat = self.env['res.company'].browse(self.env.company.id).vat

        carrier = self.wizard_id.picking_id.carrier_id
        order = carrier.init_element('OrderSpecification')
        carrier.add_consignor(order)
        # Callback URL - specify the server to get an automatic response from the Fraktjakt Webhook to keep track of the order when it changes.
        callback_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/webhook'
        carrier.add_subelement(order, 'callback_url', callback_url)
        carrier.add_subelement(order,'shipping_product_id',self.carrier_id.fraktjakt_id)
        carrier.add_subelement(order,'reference', self.wizard_id.picking_id.name.replace('/', ' '))

        cm_uom = self.env["uom.uom"].search([('name','=',"cm")])

        default_uom = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()

        # Commodoties
        if self.wizard_id.pack_ids:
            commodities = carrier.init_subelement(order, 'commodities')

            for move in self.wizard_id.pack_ids:
                package_uom = move.pack_id.packaging_id.product_uom_id
            if not package_uom:
                package_uom = default_uom

                commodity = carrier.init_subelement(commodities, 'commodity')
                carrier.add_subelement(commodity, 'name', self.wizard_id.picking_id.name)
                carrier.add_subelement(commodity,'quantity', 1)
                carrier.add_subelement(commodity, 'shelf_position', self.wizard_id.picking_id.location_id.name)
                carrier.add_subelement(commodity, 'article_number', move.pack_id.name)
                carrier.add_subelement(commodity, 'in_own_parcel', '1')
                carrier.add_subelement(commodity, 'shipped', '1')
                carrier.add_subelement(commodity,'unit_price', str(sum(move.pack_id.quant_ids.product_id.mapped('lst_price'))))
                carrier.add_subelement(commodity,'weight', str(move.weight))
                carrier.add_subelement(commodity,'length', str(package_uom._compute_quantity(move.length,cm_uom)))
                carrier.add_subelement(commodity,'width', str(package_uom._compute_quantity(move.width,cm_uom)))
                carrier.add_subelement(commodity,'height', str(package_uom._compute_quantity(move.height,cm_uom)))
    
        # Parcels
        else:
            parcels = carrier.init_subelement(order, 'parcels')
            for package in self.wizard_id.pack_ids:
                parcel = carrier.init_subelement(parcels, 'parcel')
                carrier.add_subelement(parcel,'weight', str(package.weight))
                carrier.add_subelement(parcel,'length', str(package.length))
                carrier.add_subelement(parcel,'width', str(package.width))
                carrier.add_subelement(parcel,'height', str(package.height))

        # Sender
        sender = carrier.init_subelement(order, 'sender')
        carrier.add_subelement(sender, 'name_from', self.wizard_id.sender_id.name)
        carrier.add_subelement(sender, 'tax_id', company_vat)
        
        # Recipient
        recipient = carrier.init_subelement(order,'recipient')

        if self.wizard_id.picking_id.partner_id.company_type == 'company':
            carrier.add_subelement(recipient, 'company_to', self.wizard_id.picking_id.partner_id.name)

        carrier.add_subelement(recipient,'name_to', self.wizard_id.picking_id.partner_id.name or '')
        carrier.add_subelement(recipient,'telephone_to', self.wizard_id.picking_id.partner_id.phone or '')
        carrier.add_subelement(recipient,'mobile_to', self.wizard_id.picking_id.partner_id.mobile or '')
        carrier.add_subelement(recipient,'email_to', self.wizard_id.picking_id.partner_id.email or '')
        carrier.add_subelement(recipient, 'tax_id', str(self.wizard_id.picking_id.partner_id.vat))

        # Booking
        booking = carrier.init_subelement(order, 'booking')
        carrier.add_subelement(booking,'pickup_date', str(self.wizard_id.pickup_date) or '')
        carrier.add_subelement(booking,'driving_instructions', str(self.wizard_id.driving_instructions) or '')
        
        # Address
        if self.wizard_id.picking_id.partner_id.company_type == 'company':
            carrier.add_address(order,'address_to', self.wizard_id.reciever_id, 0)
        else:
            carrier.add_address(order,'address_to', self.wizard_id.reciever_id)
        carrier.add_address(order, 'address_from', self.wizard_id.sender_id, 0)
        
        # Choose the carrier and create the shipment
        url = self.env['ir.config_parameter'].sudo().get_param('fraktjakt_order_xml_url')
        xml = etree.tostring(order, encoding='UTF-8')
        data = {'xml': xml}
        response = requests.post(url, data=data)
        code = response.status_code
        
        record = etree.XML(response.content)
        self.wizard_id.message = response.content
        
        if len(record) and record.tag == 'result':
            code = record.find('code').text
            warning = record.find('warning_message').text
            error = record.find('error_message').text
            picking = self.wizard_id.picking_id
            picking.fraktjakt_shipmentid = record.find('shipment_id').text
            picking.fraktjakt_orderid = picking.name
            picking.fraktjakt_arrival_time = self.arrival_time
            picking.fraktjakt_price = self.price
            picking.fraktjakt_agent_info = self.agent_info
            picking.fraktjakt_agent_link = self.agent_link
            picking.carrier_id = self.carrier_id
            picking.confirm_url = record.find('access_link').text
            picking.cancel_url = record.find('cancel_link').text
                        
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

            #    self.env['mail.message'].create({
            #         'body': _("Fraktjakt %s %s %s %s\nCode %s\n%s\n" % (shipping_id,order_id,payment_link,order_confirmation_link,code,warning or error or '')),
            #         'subject': "Fraktjakt",
            #         'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
            #         'res_id': picking.id,
            #         'model': picking._name,
            #         'message_type': 'notification',})
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
    _description = 'Fraktjakt Query Package'

    wizard_id = fields.Many2one(comodel_name='fj_query')
    pack_id = fields.Many2one(string='Package', comodel_name='stock.quant.package')
    weight = fields.Float()
    height = fields.Float(related='pack_id.packaging_id.height')   #mic
    width = fields.Float(related='pack_id.packaging_id.width')   #mic
    length = fields.Float(related='pack_id.packaging_id.packaging_length')

    def _volume(self):
        for record in self:
            record.volume = record.height * record.width * record.length / 1000.0
    volume = fields.Float(compute='_volume')

class fj_query_commodity(models.TransientModel):
    _name = 'fj_query.commodity'
    _description = 'Fraktjakt Query Commodity'

    wizard_id = fields.Many2one(comodel_name='fj_query')
    move_id = fields.Many2one(string='Product', comodel_name='stock.move')
    product = fields.Many2one(related='move_id.product_id')
    name = fields.Char()
    quantity = fields.Float()
    description = fields.Char()
    price = fields.Float()
    weight = fields.Float()
    height = fields.Float()   #mic
    width = fields.Float()   #mic
    length = fields.Float()

# ~ # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: