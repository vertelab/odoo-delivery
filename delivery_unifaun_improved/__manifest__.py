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
{
'name': 'Delivery Unifaun Base - Improved',
'version': '0.2',
'summary': "Halfway-point for upgrading Unifaun Base to new structure. Separates Unifaun data and functions to it's own object (unifaun.order).",
'category': '',
'description': """
    """,
'author': 'Vertel AB',
    'license': 'AGPL-3',
'website': 'http://www.vertel.se',
'depends': ['delivery_unifaun_base'],
'data': [
    #'data/delivery_data.xml',
    'views/delivery_view.xml',
    #'views/res_config_view.xml',
    'security/ir.model.access.csv',
    ],
'installable': True,
}
