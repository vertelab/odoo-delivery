from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _prepare_barcode_wiz_vals(self, option_group):
        res = super()._prepare_barcode_wiz_vals(option_group)
        res['carrier_id'] = self.carrier_id.id
        return res