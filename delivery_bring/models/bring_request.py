# -*- coding: utf-8 -*-
# Copyright 2017 Linserv (<http://www.linserv.se>)
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

import logging
import requests
import math
import json
from lxml import etree

import datetime
from odoo.tools import float_round
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BringProvider():
    def __init__(self, prod_environment, debug_logger):
        self.debug_logger = debug_logger
        # using same url for testing and production
        self.url = 'https://api.bring.com/booking/api/booking'
        self.shipping_cost_url = 'https://api.bring.com/shippingguide/v2/products/price'
        if not prod_environment:
            self.prod_environment = False
        else:
            self.prod_environment = True

    # TODO data validation
    # def check_required_values(self):
    #     print('check_required_values')
    #

    def _create_request_xml(self, picking=None, carrier=None):

        xmlns = "http://www.bring.no/booking/"
        root = etree.Element("{" + xmlns + "}bookingRequest", nsmap={None: xmlns})

        if not self.prod_environment:
            root.set('testIndicator', 'true')
        else:
            root.set('testIndicator', 'false')

        recipient_address = self._parse_address(picking.partner_id)

        bring_customer_number = carrier.bring_customer_number

        schema_version = etree.SubElement(root, 'schemaVersion')
        schema_version = "1"
        consignments = etree.SubElement(root, 'consignments')
        consignment = etree.SubElement(consignments, 'consignment')
        consignment.set('correlationId', str(picking.name))

        # TODO scheduled date must be in the future. This field is not editable in shipping state
        shipping_date_time = etree.SubElement(consignment, 'shippingDateTime')
        scheduled_date = fields.Datetime.from_string(picking.scheduled_date)
        scheduled_date_obj = fields.Datetime.context_timestamp(picking, scheduled_date).strftime('%Y-%m-%dT%H:%M:%S')
        now = fields.Datetime.context_timestamp(picking, datetime.datetime.now()).strftime('%Y-%m-%dT%H:%M:%S')
        if scheduled_date_obj < now:
            picking.scheduled_date = datetime.datetime.now() + datetime.timedelta(minutes=30)
            scheduled_date_obj = fields.Datetime.context_timestamp \
                (picking, datetime.datetime.now() + datetime.timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%S')
        shipping_date_time.text = str(scheduled_date_obj)

        parties = etree.SubElement(consignment, 'parties')

        if picking.picking_type_code == 'outgoing':
            # sender data #####################################
            sender_address = self._parse_address(picking.picking_type_id.warehouse_id.partner_id)

            sender = etree.SubElement(parties, 'sender')
            sender_name = etree.SubElement(sender, 'name')

            if picking.company_id.name:
                sender_name.text = str(picking.company_id.name[:35]) if picking.company_id.name else ''
            else:
                sender_name.text = str(
                    picking.company_id.parent_id.name[:35]) if picking.company_id.parent_id.name else ''

            sender_address_line = etree.SubElement(sender, 'addressLine')
            sender_address_line.text = str(sender_address[:35]) if sender_address else ''

            sender_postal_code = etree.SubElement(sender, 'postalCode')
            sender_postal_code.text = str(picking.picking_type_id.warehouse_id.partner_id.zip[
                                          :35]) if picking.picking_type_id.warehouse_id.partner_id.zip else ''
            sender_city = etree.SubElement(sender, 'city')
            sender_city.text = str(picking.picking_type_id.warehouse_id.partner_id.country_id.name[
                                   :35]) if picking.picking_type_id.warehouse_id.partner_id.country_id.name else ''

            sender_country_code = etree.SubElement(sender, 'countryCode')
            sender_country_code.text = str(picking.picking_type_id.warehouse_id.partner_id.country_id.code[
                                           :35]) if picking.picking_type_id.warehouse_id.partner_id.country_id.code else ''

            # TODO which field if used
            sender_reference = etree.SubElement(sender, 'reference')
            sender_additional_address_info = etree.SubElement(sender, 'additionalAddressInfo')
            sender_contact = etree.SubElement(sender, 'contact')
            sender_contact_name = etree.SubElement(sender_contact, 'name')

            if carrier.sender_booking_email_confirmation:
                sender_contact_email = etree.SubElement(sender_contact, 'email')
                sender_contact_email.text = str(
                    picking.picking_type_id.warehouse_id.partner_id.email) if picking.picking_type_id.warehouse_id.partner_id.email else ''

            sender_contact_phoneNumber = etree.SubElement(sender_contact, 'phoneNumber')
            sender_contact_phoneNumber.text = str(
                picking.picking_type_id.warehouse_id.partner_id.phone) if picking.picking_type_id.warehouse_id.partner_id.phone else ''

            # recipient data ##################################

            recipient = etree.SubElement(parties, 'recipient')

            recipient_name = etree.SubElement(recipient, 'name')
            if picking.partner_id.name:
                recipient_name.text = str(picking.partner_id.name[:35]) if picking.partner_id.name else ''
            else:
                recipient_name.text = str(
                    picking.partner_id.parent_id.name[:35]) if picking.partner_id.parent_id.name else ''
            recipient_address_line = etree.SubElement(recipient, 'addressLine')
            recipient_address_line.text = str(picking.partner_id.street[:35]) if picking.partner_id.street else ''
            recipient_address_line_2 = etree.SubElement(recipient, 'addressLine2')
            recipient_address_line_2.text = str(picking.partner_id.street2[:35]) if picking.partner_id.street2 else ''
            recipient_postal_code = etree.SubElement(recipient, 'postalCode')
            recipient_postal_code.text = str(picking.partner_id.zip[:35]) if picking.partner_id.zip else ''
            recipient_city = etree.SubElement(recipient, 'city')
            recipient_city.text = str(
                picking.partner_id.country_id.name[:35]) if picking.partner_id.country_id.name else ''
            recipient_country_code = etree.SubElement(recipient, 'countryCode')
            recipient_country_code.text = str(
                picking.partner_id.country_id.code[:35]) if picking.partner_id.country_id.code else ''

            # TODO do we need these fields?

            recipient_reference = etree.SubElement(recipient, 'reference')
            recipient_additional_address_info = etree.SubElement(recipient, 'additionalAddressInfo')
            recipient_contact = etree.SubElement(recipient, 'contact')
            recipient_name = etree.SubElement(recipient_contact, 'name')
            recipient_name.text = str(picking.partner_id.name)[:35] if picking.partner_id.name else ''
            recipient_email = etree.SubElement(recipient_contact, 'email')
            recipient_email.text = str(picking.partner_id.email)[:35] if picking.partner_id.email else ''
            recipient_phone_number = etree.SubElement(recipient_contact, 'phoneNumber')
            recipient_phone_number.text = str(picking.partner_id.mobile)[:35] if picking.partner_id.mobile else ''

        elif picking.picking_type_code == 'incoming':
            # sender data #####################################

            sender = etree.SubElement(parties, 'sender')
            sender_name = etree.SubElement(sender, 'name')
            if picking.partner_id.name:
                sender_name.text = str(picking.partner_id.name[:35]) if picking.partner_id.name else ''
            else:
                sender_name.text = str(
                    picking.partner_id.parent_id.name[:35]) if picking.partner_id.parent_id.name else ''

            sender_address_line = etree.SubElement(sender, 'addressLine')
            sender_address_line.text = str(picking.partner_id.street[:35]) if picking.partner_id.street else ''

            sender_postal_code = etree.SubElement(sender, 'postalCode')
            sender_postal_code.text = str(picking.partner_id.zip[:35]) if picking.partner_id.zip else ''
            sender_city = etree.SubElement(sender, 'city')
            sender_city.text = str(
                picking.partner_id.country_id.name[:35]) if picking.partner_id.country_id.name else ''

            sender_country_code = etree.SubElement(sender, 'countryCode')
            sender_country_code.text = str(
                picking.partner_id.country_id.code[:35]) if picking.partner_id.country_id.code else ''

            # TODO which field if used

            sender_contact = etree.SubElement(sender, 'contact')
            sender_contact_name = etree.SubElement(sender_contact, 'name')
            sender_contact_name.text = str(picking.partner_id.name)[:35] if picking.partner_id.name else ''

            sender_contact_email = etree.SubElement(sender_contact, 'email')
            sender_contact_email.text = str(picking.partner_id.email)[:35] if picking.partner_id.email else ''

            sender_contact_phoneNumber = etree.SubElement(sender_contact, 'phoneNumber')
            sender_contact_phoneNumber.text = str(picking.partner_id.mobile)[:35] if picking.partner_id.mobile else ''

            # recipient data ##################################

            recipient_address = self._parse_address(picking.picking_type_id.warehouse_id.partner_id)

            recipient = etree.SubElement(parties, 'recipient')
            recipient_name = etree.SubElement(recipient, 'name')
            if picking.company_id.name:
                recipient_name.text = str(picking.company_id.name[:35]) if picking.company_id.name else ''
            else:
                recipient_name.text = str(
                    picking.company_id.parent_id.name[:35]) if picking.company_id.parent_id.name else ''

            recipient_address_line = etree.SubElement(recipient, 'addressLine')
            recipient_address_line.text = str(recipient_address[:35]) if recipient_address else ''

            recipient_postal_code = etree.SubElement(recipient, 'postalCode')
            recipient_postal_code.text = str(picking.picking_type_id.warehouse_id.partner_id.zip[
                                             :35]) if picking.picking_type_id.warehouse_id.partner_id.zip else ''
            recipient_city = etree.SubElement(recipient, 'city')
            recipient_city.text = str(picking.picking_type_id.warehouse_id.partner_id.country_id.name[
                                      :35]) if picking.picking_type_id.warehouse_id.partner_id.country_id.name else ''
            recipient_country_code = etree.SubElement(recipient, 'countryCode')
            recipient_country_code.text = str(picking.picking_type_id.warehouse_id.partner_id.country_id.code[
                                              :35]) if picking.picking_type_id.warehouse_id.partner_id.country_id.code else ''

            # TODO do we need these fields?

            recipient_reference = etree.SubElement(recipient, 'reference')
            recipient_additional_address_info = etree.SubElement(recipient, 'additionalAddressInfo')
            recipient_contact = etree.SubElement(recipient, 'contact')
            recipient_name = etree.SubElement(recipient_contact, 'name')
            if picking.partner_id.name:
                recipient_name.text = str(picking.partner_id.name)[:35] if picking.partner_id.name else ''
            else:
                recipient_name.text = str(picking.partner_id.parent_id.name)[
                                      :35] if picking.partner_id.parent_id.name else ''
            recipient_email = etree.SubElement(recipient_contact, 'email')
            recipient_email.text = str(
                picking.picking_type_id.warehouse_id.partner_id.email) if picking.picking_type_id.warehouse_id.partner_id.email else ''
            recipient_phone_number = etree.SubElement(recipient_contact, 'phoneNumber')
            recipient_phone_number.text = str(
                picking.picking_type_id.warehouse_id.partner_id.phone) if picking.picking_type_id.warehouse_id.partner_id.phone else ''

        # product

        product = etree.SubElement(consignment, 'product')
        id = etree.SubElement(product, 'id')
        if not carrier.bring_delivery_type:
            raise UserError(_("Please choose Bring Delivery Type"))
        id.text = str(carrier.bring_delivery_type)
        customer_number = etree.SubElement(product, 'customerNumber')
        customer_number.text = str(bring_customer_number)
        # product_services ################################################

        # services = etree.SubElement(product, 'services')
        services = etree.SubElement(product, 'additionalServices')

        # all available services ##########################################

        # TODO values should be filled

        if carrier.cash_on_delivery:
            cash_on_delivery = etree.SubElement(services, 'cashOnDelivery')
            # cash on delivery values
            cash_on_delivery_account_number = etree.SubElement(cash_on_delivery, 'accountNumber')
            cash_on_delivery_account_yype = etree.SubElement(cash_on_delivery, 'accountType')
            cash_on_delivery_amount = etree.SubElement(cash_on_delivery, 'amount')
            cash_on_delivery_currency_code = etree.SubElement(cash_on_delivery, 'currencyCode')
            cash_on_delivery_message = etree.SubElement(cash_on_delivery, 'message')
            # message value
            cash_on_delivery_value = etree.SubElement(cash_on_delivery_message, 'value')
            cash_on_delivery_type = etree.SubElement(cash_on_delivery_message, 'type')
        if carrier.flex_delivery:
            # TODO message should be unique for each order, so it should be filled in wh out order view and not in carrier options
            flex_delivery = etree.SubElement(services, 'flexDelivery')
            flex_delivery_message = etree.SubElement(flex_delivery, 'message')
            flex_delivery_message.text = str(carrier.sale_id.flex_delivery_message)[
                                         :35] if carrier.sale_id and carrier.sale_id.flex_delivery_message else ''
        # if carrier.recipient_notification:
        #     recipient_notification = etree.SubElement(services, 'recipientNotification')
        #     recipient_notification_email = etree.SubElement(recipient_notification, 'email')
        #     recipient_notification_email.text = str(picking.partner_id.email)[:35] if picking.partner_id.email else ''
        #     recipient_notification_mobile = etree.SubElement(recipient_notification, 'mobile')
        #     recipient_notification_mobile.text = str(picking.partner_id.mobile)[:35] if picking.partner_id.mobile else ''

        if carrier.recipient_notification:
            notification_service = etree.SubElement(services, 'additionalService')
            notification_service_id = etree.SubElement(notification_service, 'id')
            notification_service_id.text = 'EVARSLING'
            notification_service_email = etree.SubElement(notification_service, 'email')
            notification_service_email.text = str(picking.partner_id.email)[:35] if picking.partner_id.email else ''
            notification_service_mobile = etree.SubElement(notification_service, 'mobile')
            notification_service_mobile.text = str(picking.partner_id.mobile)[:35] if picking.partner_id.mobile else ''
        if carrier.delivery_option:
            delivery_option = etree.SubElement(services, 'deliveryOption')
            delivery_option.text = str(carrier.delivery_option_attempts)
        # TODO info in API documentation about his field
        if carrier.phone_notification:
            phone_notification = etree.SubElement(services, 'phonenotification')
        if carrier.delivery_indoors:
            delivery_indoors = etree.SubElement(services, 'deliveryIndoors')
            delivery_indoors_message = etree.SubElement(delivery_indoors, 'message')
            # TODO message should be unique for each order, so it should be filled in wh out order view and not in carrier options
            delivery_indoors_message.text = str(carrier.delivery_indoors_message)[
                                            :35] if carrier.delivery_indoors_message else ''
        if carrier.simple_delivery:
            simple_delivery = etree.SubElement(services, 'simpleDelivery')
            simple_delivery.text = 'true'
        # TODO info in API dodumentation about his field
        if carrier.saturday_delivery:
            saturday_delivery = etree.SubElement(services, 'saturdayDelivery')
            # TODO fix this
            saturday_delivery.text = 'true'
        # packages ########################################

        packages = etree.SubElement(consignment, 'packages')

        # TODO validation check if all picking lines are packed
        for pack in picking.package_ids:
            package = etree.SubElement(packages, 'package')
            package.set('correlationId', str(pack.name))
            weight_in_kg = etree.SubElement(package, 'weightInKg')
            if not pack.shipping_weight:
                pack.shipping_weight = 0.1
            weight_in_kg.text = str(pack.shipping_weight)

            goods_description = etree.SubElement(package, 'goodsDescription')
            goods_description.text = str(pack.name)
            dimensions = etree.SubElement(package, 'dimensions')
            height_in_cm = etree.SubElement(dimensions, 'heightInCm')
            height_in_cm.text = str(pack.packaging_id.height)
            width_in_cm = etree.SubElement(dimensions, 'widthInCm')
            width_in_cm.text = str(pack.packaging_id.width)
            length_in_cm = etree.SubElement(dimensions, 'lengthInCm')
            length_in_cm.text = str(pack.packaging_id.length)

            # specific for specific sending methods

            # TODO this doesnt work, still getting error about volume field.
            #  There is only one field volumeInDm3 in documentation
            if carrier.bring_delivery_type in ['BUSINESS_PALLET']:
                volume_in_dm3 = etree.SubElement(dimensions, 'volumeInDm3')
                volume_in_dm3.text = '0.5'

        # lets log formated XML
        _logger.info('XML request content:\n%s' % etree.tostring(root))

        # Create Audit Log
        picking.write({'audit_log': [(0, 0, {
            'date': fields.Datetime.now(),
            'data': etree.tostring(root),
            'picking_id': picking.id
        })]})

        xml_string = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True, standalone="yes")
        return xml_string

    def send_shipping(self, picking, carrier):

        # TODO add validation here, before beginning of request create

        # generate xml for request
        request_xml = self._create_request_xml(picking, carrier)
        response_data = self._send_request(request_xml, carrier)

        root = etree.fromstring(response_data)
        namespace = {'ns': 'http://www.bring.no/booking/'}

        # errors collection
        error_msg = ''
        for errors in root.findall(".//ns:errors", namespace):
            for error in errors:
                error_msg += "Error code %s: %s \n" % (error[1].text, error[2][0].text)
        if error_msg:
            raise UserError(_('There was an error/s during a shipping reservation: \n' + error_msg))

        # extracted tracking nr
        consignment_number = root.find(".//ns:consignmentNumber", namespace).text
        # both links for label and tracking
        links = root.find(".//ns:links", namespace)
        tracking = links.find("ns:tracking", namespace).text
        labels = links.find("ns:labels", namespace).text
        # package number
        package_number = root.find(".//ns:packageNumber", namespace).text

        return {'tracking_code': tracking, 'label': labels, 'consignment_number': consignment_number,
                'package_number': package_number}

    def _send_request(self, request_xml, carrier):
        url = self.url
        api_uid = carrier.bring_api_uid
        api_key = carrier.bring_api_key
        client_url = carrier.bring_client_url
        headers = {'X-MyBring-API-Uid': api_uid,
                   'X-MyBring-API-Key': api_key,
                   'X-Bring-Client-URL': client_url,
                   'Content-Type': 'application/xml',
                   'Accept': 'application/xml'}

        # TODO test services
        # new_url = 'https://api.bring.com/booking/api/customers.xml'
        # r1 = requests.get(new_url, headers=headers)

        r = requests.post(url, data=request_xml, headers=headers)

        _logger.info('XML response:\n%s' % r.content)

        if not r.status_code == 200:
            raise UserError(_(r.content))

        else:
            return r.content

    @staticmethod
    def _parse_address(partner):
        street_name = u'%s %s' % (partner.street, partner.street2 if partner.street2 else '')
        return street_name

    def check_required_value(self, carrier, shipper, recipient, order=False, picking=False):
        recipient_required_field = ['zip', 'country_id']
        shipper_required_field = ['zip', 'country_id']

        if not carrier.bring_customer_number:
            return _("Bring Customer Number is missing, please modify your delivery method settings.")
        if not carrier.bring_api_key:
            return _("Bring API key is missing, please modify your delivery method settings.")
        if not carrier.bring_api_uid:
            return _("Bring API UID is missing, please modify your delivery method settings.")

        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The address of your company is missing or wrong (Missing field(s) :  \n %s)") % ", ".join(
                res).replace("_id", "")

        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The recipient address is missing or wrong (Missing field(s) :  \n %s)") % ", ".join(res).replace(
                "_id", "")

        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            for line in order.order_line.filtered(
                    lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type not in [
                        'service', 'digital', False]):
                return _("The estimated price cannot be computed because the weight of your product is missing.")
        return False

    def get_rate(self, order, carrier, shipper, recipient):
        dict_response = {'price': 0.0, 'currency_code': "SEK"}
        prec_pp = order.env['decimal.precision'].precision_get('Product Price')
        request_params = self._create_shipping_cost_request_params(order, carrier, shipper, recipient)
        response = self._send_rest_request(request_params, carrier)

        try:
            json_data = json.loads(response.text)
        except:
            _logger.info('JSON could not be extracted from response:\n%s' % response.text)
            json_data = {}

        if response.status_code == 400:
            if 'fieldErrors' in json_data:
                error_msg = 'Please check request data:\n'
                for error in json_data['fieldErrors']:
                    error_msg += 'Field %s - %s,\n' % (error['field'], error['message'])
                dict_response['error_message'] = error_msg
            else:
                error_msg = response.content
                dict_response['error_message'] = error_msg
            return dict_response
        elif not response.status_code == 200:
            raise UserError(_(response.content))

        if 'consignments' in json_data and json_data['consignments'][0] and 'products' in json_data['consignments'][
            0] and json_data['consignments'][0]['products'][0]:
            if 'errors' in json_data['consignments'][0]['products'][0]:
                dict_response['error_message'] = json_data['consignments'][0]['products'][0]['errors'][0]['description']
                return dict_response
            if 'warnings' in json_data['consignments'][0]['products'][0]:
                dict_response['error_message'] = json_data['consignments'][0]['products'][0]['warnings'][0][
                    'description']
                return dict_response

        # todo need to add multiple consignments?
        consignment = json_data['consignments'][0]
        price = consignment['products'][0]['price']['netPrice']['priceWithoutAdditionalServices']['amountWithVAT']
        price = float_round(float(price), precision_digits=prec_pp)
        currency_code = consignment['products'][0]['price']['netPrice']['currencyCode']
        dict_response['traceMessages'] = ' '.join(json_data['traceMessages'])

        if order.currency_id.name == currency_code:
            dict_response['price'] = price
        else:
            quote_currency = order.env['res.currency'].search([('name', '=', currency_code)], limit=1)
            price = quote_currency._convert(price, order.currency_id, order.company_id,
                                            order.date_order or fields.Date.today())
            dict_response['price'] = price
        return dict_response

    def _create_shipping_cost_request_params(self, order, carrier, shipper, recipient):
        """
        Creating parameters dict for rest call
        :param order:
        :param carrier:
        :param shipper:
        :param recipient:
        :return: dict
        """
        weight = sum([(line.product_id.weight * line.product_qty) for line in order.order_line]) or 0.0
        params = dict()
        params['fromcountry'] = shipper.country_id.code
        params['tocountry'] = recipient.country_id.code
        params['frompostalcode'] = shipper.zip.strip().replace(" ", "")
        params['topostalcode'] = recipient.zip.strip().replace(" ", "")
        params['product'] = carrier.bring_delivery_type
        params['weight'] = math.ceil(weight)
        params['customernumber'] = carrier.bring_customer_number
        return params

    def _send_rest_request(self, request_params, carrier):
        url = self.shipping_cost_url
        api_uid = carrier.bring_api_uid
        api_key = carrier.bring_api_key
        headers = {'X-MyBring-API-Uid': api_uid,
                   'X-MyBring-API-Key': api_key,
                   'Content-Type': 'application/json',
                   }
        _logger.info('request params:\n%s' % request_params)

        try:
            resp = requests.get(url, params=request_params, headers=headers)
            _logger.info('XML response:\n%s' % resp.content)

        except UserError as e:
            raise UserError(e)
        return resp
