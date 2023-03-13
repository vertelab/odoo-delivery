# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, Open Source Management Solution, third party addon
# Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
'name': 'Delivery Fraktjakt',
'version': '14.0.0.0',
'summary': 'Integrate Delivery with Fraktjakt',
'category': '',
'description': """
    """,
'author': 'Vertel AB',
    #'license': 'AGPL-3',
'website': 'http://www.vertel.se',
'depends': ['delivery','delivery_unifaun_base','base'],
'data': [
    'views/delivery_view.xml',
    'views/res_config_view.xml',
    'data/delivery_data.xml',
    'security/ir.model.access.csv'
    # ~ 'res_config_view.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
