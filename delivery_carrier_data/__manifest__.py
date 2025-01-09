# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, Open Source Management Solution, third party addon
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
    'name': 'Delivery Carrier Data',
    'version': '1.0',
    'summary': 'Add extra input field to delivery method',
    'category': 'stock',
    'description': """
Show input field in check out form in website_sale
================================================== 
Financed by Cavarosa LTD
Is meant to be inherited and other modules will fill the input field.
""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'https://vertel.se/apps/odoo-delivery/delivery_carrier_data',
    'images': ['static/description/banner.png'],  # 560x280 px.
    'depends': [
        'delivery', 'website', 'sale', 'website_sale', 
    ],
    'data': [
        'views/delivery_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'delivery_carrier_data/static/src/js/main.js',
            'delivery_carrier_data/static/src/js/website_sale_delivery.js',
        ],
    },
    'installable': True,
}
