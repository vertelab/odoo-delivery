import logging

from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class WizStockBarcodesReadPicking(models.TransientModel):
    _inherit = "wiz.stock.barcodes.read.picking"

    def action_validate_picking(self):
        # for candidate_picking in self.candidate_picking_ids:
        valid, result = self.candidate_picking_ids.with_context(
            wiz_barcode_id=self.id,
            picking_id=self.picking_id.id,
            skip_sms=True,
            skip_immediate=True,
        ).action_validate_picking()
        if not valid:
            return result

        # fraktjakt shipment query
        return self.picking_id.fraktjakt_query()

        # action = self.env["ir.actions.actions"]._for_xml_id(
        #     "stock_barcodes.stock_barcodes_action_picking_tree_ready"
        # )
        #
        # if self.picking_id and self.picking_id.picking_type_id:
        #     context = self.env.context.copy()
        #     context.update(safe_eval(action["context"]))
        #     context.update(
        #         {"search_default_picking_type_id": self.picking_id.picking_type_id.id}
        #     )
        #     action["context"] = context
        #
        # return action
