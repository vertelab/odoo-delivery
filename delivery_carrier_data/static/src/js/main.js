odoo.define('delivery_carrier_data.checkout', function (require) {
    'use strict';

    var core = require('web.core');
    var rpc = require('web.rpc');
    var publicWidget = require('web.public.widget');

    var _t = core._t;
    var concurrency = require('web.concurrency');
    var dp = new concurrency.DropPrevious();


    publicWidget.registry.CustomDelivery = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        events: Object.assign({}, publicWidget.Widget.prototype.events, {
            'change select[name="carrier_data"]': '_onSetDeliveryAddress',
        }),


        _onSetDeliveryAddress: async function (ev) {
            const carrier_id = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(
                'input[type="radio"]'
            );

            var $carrier_data = $(ev.currentTarget)

            if ($carrier_data) {
                await rpc.query({
                    route: "/shop/delivery/carrier_data",
                    params: {
                        carrier_id: carrier_id.value,
                        carrier_data: $carrier_data.val(),
                    }
                });
            }
        },
    })
})