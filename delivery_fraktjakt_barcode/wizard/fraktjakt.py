import base64
import requests
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from lxml import etree
import urllib.parse

import logging

_logger = logging.getLogger(__name__)


class FjQueryLine(models.TransientModel):
    _inherit = 'fj_query.line'
    
    
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
            carrier.add_subelement(recipient, 'company_to',  self.wizard_id.picking_id.partner_id.name)
        elif self.wizard_id.picking_id.partner_id.type == "delivery" and self.wizard_id.picking_id.partner_id.commercial_partner_id.company_type == 'company':
            carrier.add_subelement(recipient, 'company_to',  self.wizard_id.picking_id.partner_id.commercial_partner_id.name)
        
        #Should not set if we are sending to a company
        #TODO So i partner is of type conact or if its a delivery adress beloning to a contact.
        carrier.add_subelement(recipient, 'name_to', self.wizard_id.picking_id.partner_id.name or self.wizard_id.picking_id.partner_id.commercial_partner_id.name or '')
        
        carrier.add_subelement(recipient, 'telephone_to', self.wizard_id.picking_id.partner_id.phone or '')
        carrier.add_subelement(recipient, 'mobile_to', self.wizard_id.picking_id.partner_id.mobile or self.wizard_id.picking_id.partner_id.phone or '')
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
        #raise UserError(f"{data=}")
        response = requests.post(url, data=data)
        code = response.status_code
        _logger.warning(f"{response=}")
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
                if self.env.context.get('active_model') == 'wiz.stock.barcodes.read.picking':
                    return self.stock_barcodes_action_picking()
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
    

    def stock_barcodes_action_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_barcodes.stock_barcodes_action_picking_tree_ready"
        )

        if self.wizard_id.picking_id and self.wizard_id.picking_id.picking_type_id:
            context = self.env.context.copy()
            context.update(safe_eval(action["context"]))
            context.update({
                "search_default_picking_type_id": self.wizard_id.picking_id.picking_type_id.id
            })
            action["context"] = context

        return action
