import odoo.exceptions
from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
import odoo.addons.website_sale.controllers.main

import logging

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    home_delivery = fields.Boolean(string="Home Delivery",
                                   help="Check this field if the Carrier Type is home delivery.")

    def _carrier_data(self):
        for pickup in self:
            if pickup.pickup_location:
                pickup.carrier_data = _(
                        '<select name="carrier_data" t-att-data-test="pickup.name" class="selectpicker form-control '
                        'carrier_select" data-style="btn-primary"><option value="1">Choose location</option>%s</select>') \
                    % \
                    '\n'.join(['<option value="%s">%s</option>' % (p.id, p.name) for p in
                               pickup.env['res.partner'].search([('pickup_location', '=', True)])])
            if pickup.home_delivery:
                user_partner_address = self.env.user.partner_id.child_ids.filtered(
                    lambda child_partner: child_partner.type == 'delivery')
                pickup.carrier_data = _(
                        '<div><select name="carrier_data" t-att-data-test="pickup.name" class="selectpicker form-control '
                        'carrier_select" data-style="btn-primary"><option value="1">Choose location</option>%s</select>'
                        '<strong>Note: You need to login to select available home delivery options</strong></div>') \
                    % '\n'.join(['<option value="%s">%s</option>' % (p.id, p.street) for p in user_partner_address])
            else:
                super(DeliveryCarrier, pickup)._carrier_data()

    @api.model
    def lookup_carrier(self, carrier_id, carrier_data, order):
        carrier = self.env['delivery.carrier'].sudo().browse(int(carrier_id))
        if carrier and (carrier.pickup_location or carrier.home_delivery):
            if not carrier_data == '1':
                location = self.env['res.partner'].sudo().browse(int(carrier_data or 1))
                # assert location.pickup_location or location.home_delivery
                order.partner_shipping_id = location.id
        else:
            super(DeliveryCarrier, self).lookup_carrier(carrier_id, carrier_data, order)