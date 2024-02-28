# -*- coding: utf-8 -*-
# Copyright 2017 Linserv (<http://www.linserv.se>)
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    package_carrier_type = fields.Selection(selection_add=[('bring', 'Bring')])