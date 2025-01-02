# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from datetime import datetime
from werkzeug.exceptions import Forbidden, NotFound

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)

class ExtendWebsiteSale(WebsiteSale):

    def checkout_check_address(self, order):
        #I would like to call super but it returns a method where i cant see the partner so i can't check if its a a pickup location which will couse a forbidden error since the adress does not belong to the user.
        #result = super().checkout_check_address(order)
        partner_invoice = order.partner_invoice_id
        if not self._check_billing_partner_mandatory_fields(partner_invoice):
            return request.redirect('/shop/address?partner_id=%d&mode=billing' % partner_invoice.id)

        partner_shipping = order.partner_shipping_id
        ##Addtions just return the invoice address.
        if order.partner_shipping_id != order.partner_id and order.partner_shipping_id.pickup_location:
           return request.redirect('/shop/address?partner_id=%d&mode=shipping' % order.partner_invoice_id.id)
        ##Addtions

        if not order.only_services and not self._check_shipping_partner_mandatory_fields(partner_shipping):
            return request.redirect('/shop/address?partner_id=%d&mode=shipping' % partner_shipping.id)
