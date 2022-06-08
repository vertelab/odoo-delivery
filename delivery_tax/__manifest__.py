################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 N-Development (<https://n-development.com>).
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
################################################################################

{
    'name': 'Delivery: Delivery Tax',
    'version': '14.0.0.0.1',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Adds the current taxes to the shipment-cost.',
    'category': 'Inventory',
    'description': """
        Supersedes rate_shipment in the DeliveryCarrier class and adds a new
        'price_tax' key that contains the shipment price with included tax.
    """,
    #'sequence': '1',
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'https://vertel.se/apps/odoo-delivery/delivery-tax',
    'images': ['/static/description/banner.png'], # 560x280 px.
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-delivery',
    'installable': True,
}
