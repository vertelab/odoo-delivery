# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2016-TODAY Linserv Aktiebolag, Sweden (<http://www.linserv.se>).
#
##############################################################################
{
    "name": "Bring Delivery Service",
    "version": "14.0.1.28",
    "author": "Linserv AB",
    "category": "Warehouse",
    "summary": "Bring Delivery Service",
    "website": "www.linserv.se",
    "contributors": [
        'Gediminas Venclova <gediminasv@live.com>',
        'Fredrik Arvas <fredrik.arvas@linserv.se>',
        'Miracle A <iammiracle@theodooguy.com>'
    ],
    "license": "",
    "depends": ['delivery', 'mail'],
    'description': """
        
        Modification adds new delivery service - Bring. 
        Please see backend specification at - https://developer.bring.com/api/booking/
        
        Notes:
        In inventory settings please set - 'Delivery Packages' option to True
        See Documentation belop.
        
        Release History:
        v0.224 Added link to Developer API and added one Delivery-service.
        v0.225 Added Return shipments.
        v0.226 Removed one line in Shipment options and cleaned Manual.
        v0.227 Changed back to http://www.bring.no/booking/ line 34  and 229
        v0.228 Updated the recipient email and mobile number in order to get notification (yet to be confirmed)
        v0.229 Update the name when creating delivery label
        v0.230 Added Audit Log
        v0.231 Added PICKUP_PARCEL and corrected HOME_DELIVERY_PARCEL description
        - v12.0.1.24 Added custom tracking link for customers from NO SV and the rest of the world
        - v12.0.1.25 Added cost shipping cost calculation method, and flex delivery option
        - v12.0.1.26 Improved error handling
        - v12.0.1.27 Added option not to include senders email in delivery.
        - v12.0.1.28 improved price calculation method
        

    """,
    "demo": [],
    'data': [
        'views/delivery_inherited.xml',
        'views/stock_picking_inherited.xml',
        'views/res_config_inherited.xml',
        'data/delivery_bring_data.xml',

        'security/ir.model.access.csv'

    ],
    'images': ['images/LinservBringApp_v01.jpg'],

    "test": [],
    "js": [],
    "css": [],
    "qweb": [],
    "installable": True,
    "auto_install": False,
}

