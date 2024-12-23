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
    'name': 'Delivery: Home Delivery Option',
    'version': '0.1',
    'summary': "Home Delivery for Cavarosawine Customers",
    'category': 'stock',
    'description': """Home Delivery for Cavarosawine Customers""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'https://vertel.se/apps/odoo-delivery/delivery_home_delivery',
    'images': ['static/description/banner.png'], # 560x280 px.
    'depends': ['delivery_carrier_data', 'delivery_pickup', 'website_sale'],
    'data': [
        'views/delivery_view.xml',
        'views/sale_order_view.xml',
    ],
    'installable': True,
}
