/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.CustomDelivery = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'change select[name="carrier_data"]': '_onSetDeliveryAddress',
    }),

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    start: async function () {
        await this._super(...arguments);
        await this.rpc('/shop/delivery/reset_delivery_partner');
    },

    _handleCarrierUpdateResultBadge: function (result) {
        var $carrierBadge = $('#delivery_carrier input[name="delivery_type"][value=' + result.carrier_id + '] ~ .o_wsale_delivery_badge_price');

        if (result.status === true) {
             // if free delivery (`free_over` field), show 'Free', not '$0'
             if (result.is_free_delivery) {
                 $carrierBadge.text(_t('Free'));
             } else {
                 $carrierBadge.html(result.new_amount_delivery);
             }
             $carrierBadge.removeClass('o_wsale_delivery_carrier_error');
        } else {
            $carrierBadge.addClass('o_wsale_delivery_carrier_error');
            $carrierBadge.text(result.error_message);
        }
    },

    _onSetDeliveryAddress: async function (ev) {
        const radio = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(
            'input[type="radio"]'
        );
        const carrier_id = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(
            'input[type="radio"]'
        );
        var $carrier_data = $(ev.currentTarget)

        if ($carrier_data) {
            const result = await this.rpc('/shop/delivery/carrier_data', {
                'carrier_id': parseInt(carrier_id.value),
                'carrier_location': parseInt($carrier_data.val()),
            })
            this._handleCarrierUpdateResultBadge(result);
        }
    },
})
