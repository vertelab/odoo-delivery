/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteSaleDelivery.include({

    _onSetDeliveryAddress: async function (ev, carrierInput) {
        const carrier_location = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(
            'select[name="carrier_data"]'
        );

        if (carrierInput && carrier_location && carrier_location.value) {
            const result = await this.rpc('/shop/delivery/carrier_data', {
                'carrier_id': parseInt(carrierInput.value),
                'carrier_location': parseInt(carrier_location.value),
            })
            this._handleCarrierUpdateResultBadge(result);
        }

    },

    _onCarrierClick: async function (ev) {
        const radio = ev.currentTarget.closest('.o_delivery_carrier_select').querySelector(
            'input[type="radio"]'
        );
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

        this._onSetDeliveryAddress(ev, radio)
    },

})