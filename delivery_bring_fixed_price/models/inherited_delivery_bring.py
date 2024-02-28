# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProviderBringdeliveryBringFixedPrice(models.Model):
    _inherit = 'delivery.carrier'

    bring_fixed_price = fields.Boolean('Fixed Price')

    def bring_rate_shipment(self, order):
        """
        Using standard fixed price method to calculate shipping price if bring_fixed_price field is set to True
        :param order:
        :return:
        """
        if self.bring_fixed_price:
            return self.fixed_rate_shipment(order)
        res = super(ProviderBringdeliveryBringFixedPrice, self).bring_rate_shipment(order)
        return res
