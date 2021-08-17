# -*- coding: utf-8 -*-

from odoo import models, fields, api

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def rate_shipment(self, order):
        res = super(DeliveryCarrier, self).rate_shipment(order)

        self.ensure_one()
        if hasattr(self, '%s_rate_shipment' % self.delivery_type):
            
            for line in order.order_line:
                if line.product_id == self.product_id:
                    res['price_tax'] = order.order_line.tax_id.compute_all(res['price'], line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)['total_included']
        return res
