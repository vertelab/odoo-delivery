# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2016-TODAY Linserv Aktiebolag, Sweden (<http://www.linserv.se>).
#
##############################################################################
{
    "name": "Bring Delivery Service Fixed Price",
    "version": "14.0.1.01",
    "author": "Linserv AB",
    "category": "Warehouse",
    "summary": "Bring Delivery Service Fixed Price",
    "website": "www.linserv.se",
    "contributors": [
        'Gediminas Venclova <gediminasvenc@gmail.com>',
    ],
    "license": "",
    "depends": ['delivery_bring'],
    'description': """

        Modification adds new option, which allows to set fixed price for bring shipping method

    """,
    "demo": [],
    'data': [
        'views/inherited_delivery_bring.xml'
    ],
    "test": [],
    "js": [],
    "css": [],
    "qweb": [],
    "installable": True,
    "auto_install": False,
}
