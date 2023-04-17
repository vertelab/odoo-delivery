import odoo.exceptions
from odoo import models, fields, api, _
from odoo import http
from odoo.exceptions import AccessError, UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Shipping Address', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)

    def _create_payment_transaction(self, vals):
        if any([not so.delivery_partner_shipping_id for so in self]):
            print("delivery option")
            raise ValidationError(_('You need to select a delivery option.'))
        return super()._create_payment_transaction(vals)