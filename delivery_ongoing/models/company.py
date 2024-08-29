from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    ongoing_wsdl = fields.Char()
    ongoing_username = fields.Char()
    ongoing_password = fields.Char()
