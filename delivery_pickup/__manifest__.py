# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2024- Vertel AB (<http://vertel.se>).
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
    'name': 'Delivery: Delivery Pickup',
    'version': '1.0',
    'summary': 'Delivery to a pickup location',
    'category': 'stock',
    'description': """
        Delivery is made to a special pickup location. This pickup location is written to sale order delivery adress.
    
        Pickup location is a res partner marked as this.
    
    Financed by Cavarosa LTD""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'https://vertel.se/apps/odoo-delivery/delivery_pickup',
    'images': ['static/description/banner.png'], # 560x280 px.
    'depends': ['delivery', 'delivery_carrier_data'],
    'data': ['views/res_partner_inherit_view.xml', 'views/delivery_view.xml'],
    'assets': {
        'web.assets_frontend': [
            'delivery_pickup/static/js/main.js',
            # 'delivery_pickup/static/css/main.css',
        ],
    },
    'installable': True,
}
