odoo.define( function (require) {

    // When choosing an delivery carrier, update the quotation and the acquirers
    var $carrier = $("#delivery_carrier");

   

 function get_delivery_carrier() {

    $carrier.find("[name='carrier_data']").change(function (ev) {
        var carrier_data = $(ev.currentTarget).val();
        var carrier_id = $(ev.currentTarget).closest('label').find("input[name='delivery_type']").val();

 
          this._rpc({
            route: "/shop/delivery/carrier_data",
            params: {
                carrier_id: 'carrier_id',
                carrier_data: 'carrier_data',
            }
      });

});
}


    $("#delivery_carrier").find("ul").find("input[name=delivery_type]").each(function() {
        if (!$(this).is(':checked')) {
            $(this).parent().find("input[name=carrier_data]").attr('disabled', 'disabled');
        }
    });

    $("input[name=delivery_type]").on("change", function() {
        $("#delivery_carrier").find("ul").find("input[name=delivery_type]").each(function() {
            if ($(this).is(':checked')) {
                $(this).parent().find("input[name=carrier_data]").removeAttr('disabled');
            }
            else {
                $(this).parent().find("input[name=carrier_data]").attr('disabled', 'disabled');
            }
        });
    });

});

