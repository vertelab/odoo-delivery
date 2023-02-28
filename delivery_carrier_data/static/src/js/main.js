odoo.define( function (require) {

    // When choosing an delivery carrier, update the quotation and the acquirers
    var $carrier = $("#delivery_carrier");
    var rpc = require('web.rpc');


 function get_delivery_carrier() {
    
    $carrier.find("[name='carrier_data']").change(function (ev) {
        var carrier_data = $(ev.currentTarget).val();
        var carrier_id = $(ev.currentTarget).closest('li').find("input[name='delivery_type']").val();

	console.log("carrier_data was interacted with, selected: ");
	console.log(carrier_data);
	console.log(carrier_id);
 
        //this._rpc({
        rpc.query({
	    route: "/shop/delivery/carrier_data",
	    params: {
	        carrier_id: carrier_id,
	        carrier_data: carrier_data,
	    }
        });

    });
}

get_delivery_carrier();


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

