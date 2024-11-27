/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.CustomDelivery = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'change select[name="carrier_data"]': '_onSetDeliveryAddress',
    }),

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    _onSetDeliveryAddress: async function (ev) {
        const carrier_id = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(
            'input[type="radio"]'
        );
        var $carrier_data = $(ev.currentTarget)

        if ($carrier_data) {
            await this.rpc('/shop/delivery/carrier_data', {
                'carrier_id': carrier_id.value,
                'carrier_data': $carrier_data.val(),
            })
        }

    },
})
