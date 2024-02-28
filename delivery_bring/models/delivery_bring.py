# -*- coding: utf-8 -*-
# Copyright 2017 Linserv (<http://www.linserv.se>)
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests

from .bring_request import BringProvider


class ProviderBring(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('bring', 'Bring')], ondelete={'bring': 'set default'})
    bring_customer_number = fields.Char(string="Bring Customer Number", default='PARCELS_SWEDEN-123456789')
    bring_api_key = fields.Char(string="Api Key", default='1234567890123456789012345678901234567890')
    bring_api_uid = fields.Char(string="Api Uid", default='info@company.se')
    bring_client_url = fields.Char(string="Client URL", default='http://www.company.se/')

    #
    # These services are collected from: developer.bring.com/api/services/#booking
    #
    bring_delivery_type = fields.Selection([
        ('BUSINESS_PARCEL', 'SE - Business Parcel'),
        ('BUSINESS_PARCEL_BULK', 'SE - Business Parcel Bulk'),
        ('BUSINESS_PALLET', 'SE - Business Pallet'),
        ('BUSINESS_HALFPALLET', 'SE - Business Halfpallet'),
        ('BUSINESS_QUARTERPALLET', 'SE - Business Quarterpallet'),
        ('EXPRESS_NORDIC_0900', 'SE - Express Nordic 0900'),
        ('EXPRESS_NORDIC_0900_BULK', 'SE - Express Nordic 0900 Bulk'),
        ('HOME_DELIVERY_PARCEL', 'SE - Home Delivery Parcel '),
        ('PICKUP_PARCEL', 'SE - Pickup Parcel'),
        ('PICKUP_PARCEL_BULK', 'SE - Pickup Parcel Bulk'),
        ('PICKUP_PARCEL_RETURN', 'SE - PickUp Parcel Return'),
        ('PICKUP_PARCEL_RETURN_BULK', 'SE - PickUp Parcel Return Bulk'),
        ('BUSINESS_PARCEL_RETURN', 'SE - Business Parcel Return'),
        ('BUSINESS_PARCEL_RETURN_BULK', 'SE - Business Parcel Return Bulk'),
        ('BPAKKE_DOR-DOR', 'NO - BPAKKE_DOR-DOR'),
        ('BPAKKE_DOR-DOR_RETURSERVICE', 'NO - BPAKKE_DOR-DOR_RETURSERVICE'),
        ('BUSINESS_PARCEL', 'NO - BUSINESS_PARCEL'),
        ('BUSINESS_PARCEL_BULK', 'NO - BUSINESS_PARCEL_BULK'),
        ('BUSINESS_PALLET', 'NO - BUSINESS_PALLET'),
        ('BUSINESS_HALFPALLET', 'NO - BUSINESS_HALFPALLET'),
        ('BUSINESS_QUARTERPALLET', 'NO - BUSINESS_QUARTERPALLET'),
        ('EKSPRESS09', 'NO - EKSPRESS09'),
        ('EKSPRESS09_RETURSERVICE', 'NO - EKSPRESS09_RETURSERVICE'),
        ('EXPRESS_NORDIC_0900', 'NO - EXPRESS_NORDIC_0900'),
        ('EXPRESS_NORDIC_0900_BULK', 'NO - EXPRESS_NORDIC_0900_BULK'),
        ('HOME_DELIVERY_PARCEL', 'NO - HOME_DELIVERY_PARCEL'),
        ('PA_DOREN', 'NO - PA_DOREN'),
        ('PICKUP_PARCEL', 'NO - PICKUP_PARCEL'),
        ('PICKUP_PARCEL_BULK', 'NO - PICKUP_PARCEL_BULK'),
        ('SERVICEPAKKE', 'NO - SERVICEPAKKE'),
        ('SERVICEPAKKE_RETURSERVICE', 'NO - SERVICEPAKKE_RETURSERVICE'),
        ('PICKUP_PARCEL_RETURN', 'NO - PickUp Parcel Return'),
        ('PICKUP_PARCEL_RETURN_BULK', 'NO - PickUp Parcel Return Bulk'),
        ('BUSINESS_PARCEL_RETURN', 'NO - Business Parcel Return'),
        ('BUSINESS_PARCEL_RETURN_BULK', 'NO - Business Parcel Return Bulk'),

    ], String="Bring Delivery Type")

    cash_on_delivery = fields.Boolean(default=False)
    recipient_notification = fields.Boolean(default=False)
    simple_delivery = fields.Boolean(default=False)
    saturday_delivery = fields.Boolean(default=False)

    delivery_option = fields.Boolean(default=False)
    delivery_option_attempts = fields.Selection([
        ('ONE_DELIVERY_THEN_PIB', 'ONE_DELIVERY_THEN_PIB'),
        ('TWO_DELIVERIES_THEN_PIB', 'TWO_DELIVERIES_THEN_PIB'),
        ('TWO_DELIVERIES_THEN_RETURN', 'TWO_DELIVERIES_THEN_RETURN'),
    ], default='TWO_DELIVERIES_THEN_RETURN')

    sender_booking_email_confirmation = fields.Boolean(string='Sender Booking Confirmation Email',
                                                       help='This option is only available for outgoing deliveries')

    # todo unknown service:
    # socialControl

    # todo not used in this version
    flex_delivery = fields.Boolean(default=False)
    phone_notification = fields.Boolean(default=False)
    delivery_indoors = fields.Boolean(default=False)
    delivery_indoors_message = fields.Char(string='Delivery Indoors Message')

    def bring_rate_shipment(self, order):
        bring = BringProvider(self.prod_environment, self.log_xml)
        check_result = bring.check_required_value(self, order.warehouse_id.partner_id,
                                                  order.partner_shipping_id,
                                                  order=order)

        if check_result:
            return {'success': False,
                    'price': 0.0,
                    'error_message': check_result,
                    'warning_message': False}

        try:
            response = bring.get_rate(order, self, order.warehouse_id.partner_id, order.partner_shipping_id)

        except UserError as e:
            return {'success': False,
                    'price': 0.0,
                    'error_message': e.name,
                    'warning_message': False}

        if response.get('error_message'):
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error:\n%s') % response['error_message'],
                    'warning_message': False}

        return {
            'success': True,
            'price': response['price'],
            'error_message': False,
            'warning_message': response.get('traceMessages', False)
        }

    def bring_send_shipping(self, pickings):
        res = []
        # I dont think it matters if we use log_xml our call is in json but i think its only some logging :-)
        bring = BringProvider(self.prod_environment, self.log_xml)

        for picking in pickings:

            shipping = bring.send_shipping(picking, self)

            tracking_link = shipping['tracking_code']
            tracking_nr = shipping['consignment_number']
            label_url = shipping['label']
            package_number = shipping['package_number']

            # todo validation

            response = requests.get(label_url)
            raw_pdf = response.content

            # posting message
            labelmsg = (_("Booking created: </b>"))
            picking.message_post(body=labelmsg, attachments=[('Label-bring-%s.%s' % (tracking_nr, "pdf"), raw_pdf)])

            # adding bring license plate package number
            picking.bring_package_number = package_number

            # adding full tracking url depending on a delivery address country
            if tracking_nr:
                if picking.partner_id.country_id and picking.partner_id.country_id.code:
                    country_code = picking.partner_id.country_id.code
                    if country_code == 'NO':
                        pass
                    elif country_code == 'SE':
                        tracking_link = 'https://tracking.bring.se/tracking/' + tracking_nr + '?lang=sv'
                else:
                    tracking_link = 'https://tracking.bring.se/tracking/' + tracking_nr + '?lang=en'

            picking.bring_tracking_url = tracking_link

            # returning standard field values
            shipping = {'exact_price': 0,
                        'tracking_number': tracking_nr,
                        }

            res = res + [shipping]
        return res

    @staticmethod
    def bring_get_tracking_link(picking):
        return picking.bring_tracking_url

    # todo - do we need cancel method?
    # def bring_cancel_shipment(self, picking):
    #     raise UserError(_("You can not cancel a Bring shipment when a shipping label has already been generated."))
