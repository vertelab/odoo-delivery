/** @odoo-module */

import publicWidget from '@web/legacy/js/public/public_widget';

//publicWidget.registry.websiteSaleDelivery = publicWidget.Widget.extend({
//    selector: '#payment_delivery_carrier_data_list',
//    events: {
//        // Addresses
//        'click #payment_delivery_carrier_data': '_changeDeliveryAddress',
//
//        // Delivery methods
//        // 'click [name="o_delivery_radio"]': '_selectDeliveryMethod',
//        // 'click [name="o_pickup_location_selector"]': '_selectPickupLocation',
//    },
//    _changeDeliveryAddress: function (ev) {
//        console.log(this)
//        console.log("Hello?")
//        console.log(ev)
//    },
//})

publicWidget.registry.websiteSaleDelivery.include({
    _onCarrierClick: async function (ev) {
        const radio = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(
            'input[type="radio"]'
        );
        console.log("radio", radio)

        var $carrier_data = $(ev.currentTarget).find('select[name="carrier_data"]')
        console.log("$carrier_data", $carrier_data)
        if ($carrier_data) {
            console.log(radio.value)
            console.log($carrier_data.val())
            await this.rpc('/shop/delivery/carrier_data', {
                'carrier_id': radio.value,
                'carrier_data': $carrier_data.val(),
            })
        }

        if (radio.checked && !this._shouldDisplayPickupLocations(ev) && !this.forceClickCarrier) {
            return;
        }
        this.forceClickCarrier = false;

        // Clear order locations on carrier change.
        const orderLocs = document.querySelectorAll('.o_order_location');
        orderLocs.forEach(loc => {
            loc.querySelector('.o_order_location_name').textContent = '';
            loc.querySelector('.o_order_location_address').textContent = '';
            const divDNone = loc.parentElement;
            if (!divDNone.classList.contains('d-none')) {
                divDNone.classList.add('d-none');
            }
        });



        this._disablePayButton();
        this._showLoading(radio);
        radio.checked = true;
        await this._onClickShowLocations(ev);
        await this._handleCarrierUpdateResult(radio);
        this._disablePayButtonNoPickupPoint(ev);
    },
})