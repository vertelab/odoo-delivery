# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Delivery Barcodes Package",
    "summary": "Select Delivery Carrier and Package Type",
    "version": "16.0.1.1.0",
    "author": "Vertel AB",
    "website": "https://vertel.se",
    "license": "AGPL-3",
    "category": "Extra Tools",
    "depends": ["stock_barcodes", "delivery"],
    "data": [
        "wizard/stock_barcodes_read_picking_views.xml",
    ],
    "installable": True,
}
