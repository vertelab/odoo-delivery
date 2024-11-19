//odoo.define( function (require) {
//
//    // When choosing an delivery carrier, update the quotation and the acquirers
//    var $carrier = $("#delivery_carrier");
//    var rpc = require('web.rpc');
//
//
// function get_delivery_carrier() {
//
//    $carrier.find("[name='carrier_data']").change(function (ev) {
//        var carrier_data = $(ev.currentTarget).val();
//        var carrier_id = $(ev.currentTarget).closest('li').find("input[name='delivery_type']").val();
//
//	console.log("carrier_data was interacted with, selected: ");
//	console.log(carrier_data);
//	console.log(carrier_id);
//
//        //this._rpc({
//        rpc.query({
//            route: "/shop/delivery/carrier_data",
//            params: {
//                carrier_id: carrier_id,
//                carrier_data: carrier_data,
//            }
//        });
//
//    });
//}
//
//get_delivery_carrier();
//
//
//    $("#delivery_carrier").find("ul").find("input[name=delivery_type]").each(function() {
//        if (!$(this).is(':checked')) {
//            $(this).parent().find("input[name=carrier_data]").attr('disabled', 'disabled');
//        }
//    });
//
//    $("input[name=delivery_type]").on("change", function() {
//        $("#delivery_carrier").find("ul").find("input[name=delivery_type]").each(function() {
//            if ($(this).is(':checked')) {
//                $(this).parent().find("input[name=carrier_data]").removeAttr('disabled');
//            }
//            else {
//                $(this).parent().find("input[name=carrier_data]").attr('disabled', 'disabled');
//            }
//        });
//    });
//
//});



odoo.define('delivery_carrier_data.checkout', function (require) {
    'use strict';

    var core = require('web.core');
    var rpc = require('web.rpc');
    var publicWidget = require('web.public.widget');

    var _t = core._t;
    var concurrency = require('web.concurrency');
    var dp = new concurrency.DropPrevious();


    publicWidget.registry.websiteSaleDelivery.include({

        _onCarrierClick: function (ev) {
            var $radio = $(ev.currentTarget).find('input[type="radio"]');

            var $carrier_data = $(ev.currentTarget).find('select[name="carrier_data"]')
            if ($carrier_data) {
                rpc.query({
                    route: "/shop/delivery/carrier_data",
                    params: {
                        carrier_id: $radio.val(),
                        carrier_data: $carrier_data.val(),
                    }
                });

            }

            this._showLoading($radio);
            $radio.prop("checked", true);
            var $payButton = $('#o_payment_form_pay');
            $payButton.prop('disabled', true);
            var disabledReasons = $payButton.data('disabled_reasons') || {};
            disabledReasons.carrier_selection = true;
            $payButton.data('disabled_reasons', disabledReasons);
            dp.add(this._rpc({
                route: '/shop/update_carrier',
                params: {
                    carrier_id: $radio.val(),
                },
            })).then(this._handleCarrierUpdateResult.bind(this));
        },

    })

})