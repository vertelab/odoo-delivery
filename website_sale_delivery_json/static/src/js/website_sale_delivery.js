$(document).ready(function () {
    // When choosing an delivery carrier, update the quotation and the acquirers
    var $carrier = $("#delivery_carrier");
    $carrier.find("input[name='delivery_type']").click(function (ev) {
        var carrier_id = $(ev.currentTarget).val();
        openerp.jsonRpc("/shop/payment/delivery_update", "call", {
            'carrier_id': carrier_id,
        }).done(function(data){
            $("#order_total").find("span.oe_currency_value").replaceWith('<span class="oe_currency_value">' + data['amount_total'] + '</span>');
            $("#order_total_taxes").find("span.oe_currency_value").replaceWith('<span class="oe_currency_value">' + data['amount_tax'] + '</span>');
            $("#order_delivery").find("span.oe_currency_value").replaceWith('<span class="oe_currency_value">' + data['amount_delivery'] + '</span>');
        });
    });
});
