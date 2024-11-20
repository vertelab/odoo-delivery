from odoo import models, fields, api, _

class ResPartner(models.Model):
    """Add some fields related to pickup locations"""
    _inherit = "res.partner"

    pickup_location = fields.Boolean(string="Pickup Location",
                                     help="Check this field if the partner is a pickup location for deliveries.")

    # @api.onchange('pickup_location')
    # def onchange_pickup_location(self):
    #     if self.pickup_location:
    #         self.supplier = True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: