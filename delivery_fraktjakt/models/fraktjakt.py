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
from odoo.exceptions import UserError
from lxml import etree
import urllib.parse

import logging

_logger = logging.getLogger(__name__)

FRAKTJAKT_API_VERSION = '4.4'


class FjQuery(models.TransientModel):
    _name = 'fj_query'
    _description = 'Fraktjakt Query'

    fraktjakt_price = fields.Float(string='Price')
    fraktjakt_agent_info = fields.Char(string='Agent info')
    fraktjakt_agent_link = fields.Char(string='Agent link')
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Picking', )
    line_ids = fields.One2many(string='Shipping products', comodel_name='fj_query.line', inverse_name='wizard_id')
    pack_ids = fields.One2many(string='Packages', comodel_name='fj_query.package', inverse_name='wizard_id')
    move_lines = fields.One2many(string='Products', comodel_name='fj_query.commodity', inverse_name='wizard_id')
    sender_id = fields.Many2one(comodel_name='res.partner', string='Sender', )
    reciever_id = fields.Many2one(comodel_name='res.partner', string='Receiver', )
    cold = fields.Boolean(string='Cold', help="Cargo contains packages that should be cold")
    freeze = fields.Boolean(string='Freeze', help="Cargo contains packages that should hold under freezing point")
    pickup = fields.Boolean(string='Pickup', )
    express = fields.Boolean(string='Express', )
    dropoff = fields.Boolean(string='Drop off', )
    green = fields.Boolean(string='Green', )
    quality = fields.Boolean(string='Quality', )
    time_guarantee = fields.Boolean(string='Time Guarantee', )
    pickup_date = fields.Date(string='Pickup Date', )
    driving_instructions = fields.Text(string='Driving Instructions', )
    # user_notes = fields.Text(string='Notes',)
    message = fields.Text()
    fraktjakt_arrival_time = fields.Char(related="picking_id.fraktjakt_arrival_time", string='Arrival Time')
    processing = fields.Boolean(string="Processing")

    def fraktjakt_query(self):
        """Create a stored shipment."""

        self.line_ids = None
        self.message = ''

        carrier = self.picking_id.carrier_id
        shipment = carrier.init_element('shipment')
        carrier.add_subelement(shipment, 'value',
                               str(sum(self.pack_ids.pack_id.quant_ids.product_id.mapped('lst_price'))))
        carrier.add_subelement(shipment, 'shipper_info', '1')
        carrier.add_consignor(shipment)
        cm_uom = self.env["uom.uom"].search([('name', '=', "cm")])

        default_uom = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()

        parcels = carrier.init_subelement(shipment, 'parcels')
        for package in self.pack_ids:
            # package_uom = package.pack_id.packaging_id.product_uom_id
            package_uom = False
            if not package_uom:
                package_uom = default_uom
            parcel = carrier.init_subelement(parcels, 'parcel')
            carrier.add_subelement(parcel, 'weight', str(package.weight))
            carrier.add_subelement(parcel, 'height', str(package_uom._compute_quantity(package.height, cm_uom)))
            carrier.add_subelement(parcel, 'width', str(package_uom._compute_quantity(package.width, cm_uom)))
            carrier.add_subelement(parcel, 'length', str(package_uom._compute_quantity(package.length, cm_uom)))

        if self.reciever_id.company_type == 'company':
            carrier.add_subelement(shipment, 'company_to', self.reciever_id.name)
            carrier.add_address(shipment, 'address_to', self.reciever_id, 0)
        else:
            carrier.add_address(shipment, 'address_to', self.reciever_id)

        carrier.add_address(shipment, 'address_from', self.sender_id, 0)
        if self.cold:
            carrier.add_subelement(shipment, 'cold', '1')
        if self.freeze:
            carrier.add_subelement(shipment, 'freeze', '1')
        if self.pickup:
            carrier.add_subelement(shipment, 'pickup', '1')
        if self.express:
            carrier.add_subelement(shipment, 'express', '1')
        if self.dropoff:
            carrier.add_subelement(shipment, 'dropoff', '1')
        if self.green:
            carrier.add_subelement(shipment, 'green', '1')
        if self.quality:
            carrier.add_subelement(shipment, 'quality', '1')
        if self.time_guarantee:
            carrier.add_subelement(shipment, 'time_guarantee', '1')
        response, code, self.message = carrier.fraktjakt_send('fraktjakt/query_xml', urllib.parse.quote_plus(
            etree.tostring(shipment, encoding='UTF-8')))
        if code in ['0', '1']:
            fj = etree.XML(response.content)
            shipping_products = fj.find('shipping_products')
            for shipping_product in fj.find('shipping_products').findall('shipping_product'):
                carrier = self.env['delivery.carrier'].search([('fraktjakt_id', '=', shipping_product.find('id').text)])
                if not carrier:
                    product_id = self.env['ir.model.data']._xmlid_lookup(
                        'delivery_fraktjakt.fraktjakt_product'
                    )[2]
                    partner_id = False
                    shipper = shipping_product.find('shipper')
                    partner = self.env['res.partner'].search([('fraktjakt_id', '=', shipper.find('id').text)])
                    if partner:
                        partner_id = partner.id
                    if not partner_id:
                        encoded_image = False
                        if shipper.find('logo_url').text:
                            image = requests.get(shipper.find('logo_url').text).content
                            encoded_image = base64.b64encode(image).decode('utf-8')
                        self.env['res.partner'].create({
                            'fraktjakt_id': shipper.find('id').text,
                            'is_company': True,
                            'name': shipper.find('name').text,
                            'image_1920': encoded_image,
                        })
                    # partner = self.env['res.partner'].search([('fraktjakt_id', '=', shipper.find('id').text)])
                    carrier = self.env['delivery.carrier'].create({
                        'fraktjakt_id': shipping_product.find('id').text,
                        'fraktjakt_desc': shipping_product.find('description').text,
                        'is_fraktjakt': True,
                        'partner_id': partner.id,
                        'product_id': product_id,
                        'name': shipping_product.find('name').text,
                    })
                self.line_ids |= self.env['fj_query.line'].create({
                    'partner_id': carrier.partner_id,
                    'image': carrier.partner_id.image_1920,
                    'carrier_id': carrier.id,
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
            'view_id': self.env['ir.model.data']._xmlid_lookup('delivery_fraktjakt.fj_query_form_view')[2],
            'view_mode': 'form',
            'target': 'new',
        }


class FjQueryLine(models.TransientModel):
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
        
        
    def add_commodity(self, carrier, commodities, stock_move_line):
        commodity = carrier.init_subelement(commodities, 'commodity')
        product = stock_move_line.product_id
        country = product.country_of_origin.code if product.country_of_origin else False
        unit_price = product.lst_price
        company = stock_move_line.company_id
        company_currency = company.currency_id
        _logger.warning(f"{company=}")
        _logger.warning(f"{company_currency=}")
        if stock_move_line.move_id and stock_move_line.move_id.sale_line_id and stock_move_line.move_id.sale_line_id.price_unit > 0:
            #Grab init price from here and convert to company_currency
            _logger.warning("Sale order line found"*100)
            sale_line = stock_move_line.move_id.sale_line_id
            price_in_so_currency = sale_line.price_unit
            _logger.warning(f"{price_in_so_currency=}")

            so_currency = sale_line.order_id.currency_id
            _logger.warning(f"{so_currency=}")

            price_in_company_currency = so_currency._convert(
                price_in_so_currency,
                company_currency,
                company,
                sale_line.order_id.date_order or fields.Date.context_today(stock_move_line)
            )
            _logger.warning(f"{price_in_company_currency=}")

            unit_price = price_in_company_currency

        carrier.add_subelement(commodity, 'name', product.name)
        carrier.add_subelement(commodity, 'quantity', stock_move_line.qty_done)
        if country:
           carrier.add_subelement(commodity, 'country_of_manufacture', country)
        carrier.add_subelement(commodity, 'shelf_position', self.wizard_id.picking_id.location_id.name)
        carrier.add_subelement(commodity, 'article_number', product.default_code)
        carrier.add_subelement(commodity, 'in_own_parcel', '0')
        carrier.add_subelement(commodity, 'shipped', '1')
        carrier.add_subelement(commodity, 'unit_price', unit_price)
        carrier.add_subelement(commodity, 'currency', company_currency.name)
        carrier.add_subelement(commodity, 'weight', str(product.weight))
        if product.hs_code:
            carrier.add_subelement(commodity, 'taric', str(product.hs_code))
        return carrier, commodity
        
        
    # Choose Carrier
    def choose_product(self):
        if not self.wizard_id.processing:
            self.wizard_id.processing = True
            self.env.cr.commit()
        else:
            raise UserError("It seems you are already processing a shipment")

        self.wizard_id.fraktjakt_arrival_time = self.arrival_time
        self.wizard_id.fraktjakt_price = self.price
        self.wizard_id.fraktjakt_agent_info = self.agent_info
        self.wizard_id.fraktjakt_agent_link = self.agent_link

        # Target sending company VAT
        company_vat = self.env['res.company'].browse(self.env.company.id).vat

        carrier = self.wizard_id.picking_id.carrier_id
        order = carrier.init_element('OrderSpecification')
        carrier.add_consignor(order)
        # Callback URL - specify the server to get an automatic response from the Fraktjakt
        # Webhook to keep track of the order when it changes.
        callback_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/webhook'
        carrier.add_subelement(order, 'callback_url', callback_url)
        carrier.add_subelement(order, 'shipping_product_id', self.carrier_id.fraktjakt_id)
        carrier.add_subelement(order, 'reference', self.wizard_id.picking_id.name.replace('/', ' '))

        cm_uom = self.env["uom.uom"].search([('name', '=', "cm")])

        default_uom = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()

        # Commodities
        if len(self.wizard_id.pack_ids) > 1:
            raise UserError("Using several packages is not implemented.")

        if self.wizard_id.pack_ids:
            commodities = carrier.init_subelement(order, 'commodities')
            parcels = carrier.init_subelement(order, 'parcels')

            for package_id in self.wizard_id.pack_ids:
                # ~ stock_move_lines_grouped = self.env['stock.move.line'].read_group(
                    # ~ [('result_package_id', '=', package_id.pack_id.id)],  # domain to filter the records
                    # ~ ['product_id', 'move_id', 'qty_done:sum'],  # fields to include in the result
                    # ~ ['product_id']  # field(s) to group by
                # ~ )
                stock_move_lines = self.env['stock.move.line'].search([('result_package_id', '=', package_id.pack_id.id),('qty_done','>',0)])
                package_uom = False
                if not package_uom:
                    package_uom = default_uom

                for stock_move_line in stock_move_lines:
                    self.add_commodity(carrier, commodities, stock_move_line)

                parcel = carrier.init_subelement(parcels, 'parcel')
                carrier.add_subelement(parcel, 'weight', str(package_id.weight))
                carrier.add_subelement(parcel, 'length', str(package_uom._compute_quantity(package_id.length, cm_uom)))
                carrier.add_subelement(parcel, 'width', str(package_uom._compute_quantity(package_id.width, cm_uom)))
                carrier.add_subelement(parcel, 'height', str(package_uom._compute_quantity(package_id.height, cm_uom)))

        # Sender
        sender = carrier.init_subelement(order, 'sender')
        carrier.add_subelement(sender, 'name_from', self.wizard_id.sender_id.name)
        carrier.add_subelement(sender, 'tax_id', company_vat)

        # Recipient
        recipient = carrier.init_subelement(order, 'recipient')

        if self.wizard_id.picking_id.partner_id.company_type == 'company':
            carrier.add_subelement(recipient, 'company_to', self.wizard_id.picking_id.partner_id.name)

        carrier.add_subelement(recipient, 'name_to', self.wizard_id.picking_id.partner_id.name or '')
        carrier.add_subelement(recipient, 'telephone_to', self.wizard_id.picking_id.partner_id.phone or '')
        carrier.add_subelement(recipient, 'mobile_to', self.wizard_id.picking_id.partner_id.mobile or '')
        carrier.add_subelement(recipient, 'email_to', self.wizard_id.picking_id.partner_id.email or '')
        carrier.add_subelement(recipient, 'tax_id', str(self.wizard_id.picking_id.partner_id.vat))
        #raise UserError("Test")
        # Booking
        booking = carrier.init_subelement(order, 'booking')
        carrier.add_subelement(booking, 'pickup_date', str(self.wizard_id.pickup_date) or '')
        carrier.add_subelement(booking, 'driving_instructions', str(self.wizard_id.driving_instructions) or '')

        # Address
        if self.wizard_id.picking_id.partner_id.company_type == 'company':
            carrier.add_address(order, 'address_to', self.wizard_id.reciever_id, 0)
        elif self.wizard_id.picking_id.partner_id.type == "delivery" and self.wizard_id.picking_id.partner_id.commercial_partner_id.company_type == 'company':
            carrier.add_address(order, 'address_to', self.wizard_id.reciever_id, 0)
        else:
            carrier.add_address(order, 'address_to', self.wizard_id.reciever_id)
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
                    'view_id':
                        self.env['ir.model.data'].get_object_reference('delivery_fraktjakt', 'fj_query_form_view')[1],
                    'view_mode': 'form',
                    'target': 'new',
                }
            else:
                shipping_id = "Shipping ID <a href='%s'>%s</a>" % (
                    carrier.get_url('shipments/show/%s' % picking.fraktjakt_shipmentid), picking.fraktjakt_shipmentid)
                order_id = "Order <a href='%s'>%s</a>" % (
                    carrier.get_url('orders/show/%s' % picking.fraktjakt_orderid), picking.fraktjakt_orderid)
                payment_link = "<href='%s'>Payment</a>" % (record.find('payment_link').text) if record.find(
                    'payment_link') else ''
                order_confirmation_link = "<href='%s'>Order confirmation</a>" % (
                    record.find('sender_email_link').text) if record.find('sender_email_link') else ''

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


class FjQueryPackage(models.TransientModel):
    _name = 'fj_query.package'
    _description = 'Fraktjakt Query Package'

    wizard_id = fields.Many2one(comodel_name='fj_query')
    pack_id = fields.Many2one(string='Package', comodel_name='stock.quant.package')
    weight = fields.Float()
    height = fields.Integer(related='pack_id.height')
    width = fields.Integer(related='pack_id.package_type_id.width')
    length = fields.Integer(related='pack_id.package_type_id.packaging_length')

    def _volume(self):
        for record in self:
            record.volume = record.height * record.width * record.length / 1000.0

    volume = fields.Float(compute='_volume')


class FjQueryCommodity(models.TransientModel):
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
    height = fields.Float()
    width = fields.Float()
    length = fields.Float()

# ~ # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
