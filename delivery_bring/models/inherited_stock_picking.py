from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DeliveryBringStockPicking(models.Model):
    _inherit = 'stock.picking'

    bring_package_number = fields.Char(string="Bring package#")
    bring_tracking_url = fields.Char(string="Bring Tracking URL")
    audit_log = fields.One2many('bring.audit.log', 'picking_id', string="Audit", readonly=True)

    def button_validate(self):
        res = super(DeliveryBringStockPicking, self).button_validate()
        if not self.has_packages and self.carrier_id and self.carrier_id.delivery_type and self.carrier_id.delivery_type == 'bring':
            raise UserError(_('No packing created for the shipment'))
        return res


class BringAudit(models.Model):
    _name = 'bring.audit.log'
    _description = 'Bring Audit Data'

    date = fields.Datetime(string="Date")
    data = fields.Char(string='XML Data')
    picking_id = fields.Many2one('stock.picking')

