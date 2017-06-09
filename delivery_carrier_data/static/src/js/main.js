$(document).ready(function () {

    // When choosing an delivery carrier, update the quotation and the acquirers
    var $carrier = $("#delivery_carrier");
    $carrier.find("[name='carrier_data']").change(function (ev) {
        var carrier_data = $(ev.currentTarget).val();
        var carrier_id = $(ev.currentTarget).closest('label').find("input[name='delivery_type']").val();
        openerp.jsonRpc("/shop/delivery/carrier_data", 'call', {
            'carrier_id': carrier_id,
            'carrier_data': carrier_data,
        })
    });

});
