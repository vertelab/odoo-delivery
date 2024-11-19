/** @odoo-module */
// import {Component, useState, xml} from "@odoo/owl";

// console.log("Before Class")
// class MyComponent extends Component {
//     setup() {
//         console.log("setup")
//         this.state = useState({ value: 1 });
//         console.log(document.getElementById('payment_delivery_carrier_data_list'))

//     }

//     log_stuff() {
//         console.log("Yo")
//         this.state.value++;
//     }
// }
// MyComponent.template = 'delivery_carrier_data.MyComponent';

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.websiteSaleDelivery = publicWidget.Widget.extend({
    selector: '#payment_delivery_carrier_data_list',
    events: {
        // Addresses
        'click #payment_delivery_carrier_data': '_changeDeliveryAddress',
     
        // Delivery methods
        // 'click [name="o_delivery_radio"]': '_selectDeliveryMethod',
        // 'click [name="o_pickup_location_selector"]': '_selectPickupLocation',
    },
    _changeDeliveryAddress: function (ev) {
        console.log(this)
        console.log("Hello?")
        console.log(ev)
    },
})