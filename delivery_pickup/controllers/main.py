# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from datetime import datetime
from werkzeug.exceptions import Forbidden, NotFound
from odoo.tools import lazy, str2bool

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class ExtendWebsiteSale(WebsiteSale):

    def checkout_check_address(self, order):
        partner_invoice = order.partner_invoice_id

        Partner = request.env['res.partner'].with_context(show_address=1).sudo()

        partners_sudo = Partner.search(
            [('id', 'child_of', order.partner_id.commercial_partner_id.ids)]
        )

        shipping_partners = partners_sudo.filtered(lambda p: p.type != 'invoice')

        if not shipping_partners:
            shipping_partners = order.partner_id

        if not self._check_billing_partner_mandatory_fields(partner_invoice):
            return request.redirect('/shop/address?partner_id=%d&mode=billing' % partner_invoice.id)

        partner_shipping = order.partner_shipping_id

        # additions just return the invoice address.
        if (order.partner_shipping_id != order.partner_id and order.partner_shipping_id.pickup_location
                and not self._check_shipping_partner_mandatory_fields(partner_shipping)):

            if order.partner_shipping_id not in partners_sudo:
                return request.redirect('/shop/address?partner_id=%d&mode=shipping' % shipping_partners[0])
            else:
                return request.redirect('/shop/address?partner_id=%d&mode=shipping' % partner_shipping)
        # end additions

        if not order.only_services and not self._check_shipping_partner_mandatory_fields(partner_shipping):
            return request.redirect('/shop/address?partner_id=%d&mode=shipping' % partner_shipping.id)

