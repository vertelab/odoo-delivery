$(document).ready(function() {
    var $pickup_sel = $("select[name='carrier_data']");
    var $pickup_input = $pickup_sel.closest("label").find("input[name='delivery_type']");
    var $submit_btn = $("div#payment_method").find("form[target='_self']").find("button[type='submit']");
    if($pickup_input.is(':checked') && $pickup_sel.val() == 1) {
        $submit_btn.attr("disabled", true);
    }
    $("input[name='delivery_type']").click(function() {
        determine_sel();
    });
    $pickup_sel.change(function() {
        determine_sel();
    });
    function determine_sel() {
        console.log("run");
        if($pickup_input.is(':checked')) {
            if($pickup_sel.val() != 1) {
                $submit_btn.attr("disabled", false);
            }
            else {
                $submit_btn.attr("disabled", true);
            }
        }
        else {
            $submit_btn.attr("disabled", false);
        }
    }
});
