# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2017- Vertel AB (<http://vertel.se>).
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
'name': 'Delivery Pickup',
'version': '0.1',
'summary': 'Delivery to a pickup location',
'category': 'stock',
'description': """
    Delivery is made to a special pickup location. This pickup location is written to sale order delivery adress.
    
    Pickup location is a res partner marked as this.
    
Financed by Cavarosa LTD""",
'author': 'Vertel AB',
'website': 'http://www.vertel.se',
'depends': ['website_sale_delivery',],
'data': ['res_partner_view.xml', 'delivery_view.xml'],
'installable': True,
}
