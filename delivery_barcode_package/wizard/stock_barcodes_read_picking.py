import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class WizStockBarcodesReadPicking(models.TransientModel):
    _inherit = "wiz.stock.barcodes.read.picking"

    carrier_id = fields.Many2one("delivery.carrier", string="Delivery Carrier")

    @api.onchange("carrier_id")
    def set_delivery_carrier(self):
        self.picking_id.carrier_id = self.carrier_id.id

    def action_put_in_pack(self):
        picking_id = self.mapped("picking_id")
        res = picking_id.action_put_in_pack()
        return res
