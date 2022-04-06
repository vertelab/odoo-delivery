# -*- coding: utf-8 -*-
{
    'name': 'Delivery Unifaun Base',
    'version': '14.1.0.0.0',
    'summary': 'Integrate Delivery with Unifaun Base-module',
    'category': '',
    'description': """
        """,
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'http://www.vertel.se',
    'depends': ['delivery'],
    'data': [
        'data/delivery_data.xml',
        'views/delivery_view.xml',
        'views/improved_delivery_view.xml',
        'views/res_config_view.xml',
        'security/ir.model.access.csv',
        ],
    'installable': True,
}
