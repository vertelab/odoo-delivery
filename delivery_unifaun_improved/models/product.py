# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)

class product_ul(models.Model):
    _name = "product.ul"
    _description = "Logistic Unit"
    
    name = fields.Char('Name', select=True, required=True, translate=True)
    type = fields.Selection([('unit','Unit'),('pack','Pack'),('box', 'Box'), ('pallet', 'Pallet')], 'Type', required=True)
    height = fields.Float('Height', help='The height of the package')
    width = fields.Float('Width', help='The width of the package')
    length = fields.Float('Length', help='The length of the package')
    weight = fields.Float('Empty Package Weight')

class LogisticalUnit(models.Model):
    _inherit = "product.ul"

    unifaun_code_ids = fields.One2many(comodel_name='product.ul.unifaun_code', inverse_name='ul_id', string='Unifaun Codes')

    @api.multi
    def get_unifaun_code(self, carrier):
        code = self.unifaun_code_ids.filtered(lambda uc: uc.carrier_id == carrier)
        return code and code.name or None

class LogisticalUnitUnifaunCode(models.Model):
    _name = 'product.ul.unifaun_code'
    _description = 'Unifaun Shipping Code'
    _sql_constraints = [
            ('unique_ul_by_carrier',
             'unique(ul_id, carrier_id)',
             "You can not have two Unifaun codes for the same carrier and logistical unit.")
        ]

    # TODO: Replace with python constraint (want to be able to have 2 without ul_id).
    # Make constraint for default
    name = fields.Char(string='Code', required=True)
    ul_id = fields.Many2one(comodel_name='product.ul', string='Logistical Unit')
    carrier_id = fields.Many2one(comodel_name='delivery.carrier', string='Carrier', required=True)
    default = fields.Boolean(string='Default Code', help="Use this code for this carrier if nothing else is specified.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
