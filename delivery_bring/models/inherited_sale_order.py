from odoo import models, fields, api, _


class DeliveryBringSaleOrder(models.Model):
    _inherit = 'sale.order'

    flex_delivery_message = fields.Char(string='Flex Delivery Driver Message')
    show_delivery_message = fields.Boolean(string='Show Flex Message To Driver', compute='compute_show_delivery_message')

    @api.onchange('carrier_id')
    def compute_show_delivery_message(self):
        for sale_order in self:
            if sale_order.carrier_id and sale_order.carrier_id.delivery_type == 'bring' and sale_order.carrier_id.flex_delivery:
                sale_order.show_delivery_message = True
            elif sale_order.carrier_id and not sale_order.carrier_id.delivery_type == 'bring':
                sale_order.flex_delivery_message = False
            else:
                sale_order.show_delivery_message = False
                sale_order.flex_delivery_message = False

                # @api.onchange('carrier_id')
    # def clean_delivery_message(self):
    #     for sale_order in self:
    #         print(sale_order.carrier_id)


