import logging


from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.delivery import WebsiteSaleDelivery, WebsiteSale
from odoo.addons.website_sale.controllers.main import PaymentPortal

from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WebsiteSaleLoyaltyDelivery(WebsiteSaleDelivery):

    def _update_website_sale_delivery_return(self, order, **post):
        result = super()._update_website_sale_delivery_return(order, **post)
        return result


class WebsiteCarrierData(WebsiteSale):

    @http.route(['/shop/delivery/carrier_data'], type='json', auth="public", website=True)
    def lookup_carrier(self, carrier_id, carrier_location, **post):
        order = request.website.sale_get_order(force_create=True)
        order.write({'delivery_partner_shipping_id': carrier_location, 'partner_shipping_id': carrier_location})
        if not int(carrier_id) in order._get_delivery_methods().ids:
            raise UserError(
                _('It seems that a delivery method is not compatible with your address. Please refresh the page and '
                  'try again.'))

        Monetary = request.env['ir.qweb.field.monetary']

        res = {'carrier_id': carrier_id}
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))
        rate = WebsiteSaleDelivery._get_rate(carrier, order)
        if rate.get('success'):
            res['status'] = True
            res['new_amount_delivery'] = Monetary.value_to_html(rate['price'], {'display_currency': order.currency_id})
            res['is_free_delivery'] = not bool(rate['price'])
            res['error_message'] = rate['warning_message']
        else:
            res['status'] = False
            res['new_amount_delivery'] = Monetary.value_to_html(0.0, {'display_currency': order.currency_id})
            res['error_message'] = rate['error_message']
        return res

    @http.route(['/shop/delivery/reset_delivery_partner'], type='json', auth="public", website=True)
    def reset_delivery_partner(self, **post):
        order = request.website.sale_get_order()
        order.write({
            'delivery_partner_shipping_id': False
        })


class PaymentPortalExtended(PaymentPortal):

    def _validate_transaction_for_order(self, transaction, sale_order_id):
        """
        Perform final checks against the transaction & sale_order.
        Override me to apply payment unrelated checks & processing
        """
        sale_order = request.env['sale.order'].browse(sale_order_id).exists()

        if not sale_order.delivery_partner_shipping_id and (
                sale_order.carrier_id.home_delivery or sale_order.carrier_id.pickup_location
        ):
            raise ValidationError(_('You need to select a delivery option.'))
        if not sale_order.campaign_id:
            raise ValidationError(_('Your order is not associated to a campaign. '
                                    'Select items from the running campaign.'))

        cart_products = sale_order.order_line.mapped('product_id').mapped('product_tmpl_id').filtered(
            lambda product: product.is_published)
        campaign_real_products = sale_order.campaign_id.product_ids

        from datetime import datetime, date

        if sale_order.order_line and date.today() > sale_order.campaign_id.date_stop and all(
                item in campaign_real_products for item in cart_products):
            raise ValidationError(_(
                'Your order is not associated to a campaign. Select items from the running campaign.'
            ))
