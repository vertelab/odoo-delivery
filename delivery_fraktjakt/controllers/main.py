# # -*- coding: utf-8 -*-
# # Part of Odoo. See LICENSE file for full copyright and licensing details.


import base64
import requests
from odoo import http
from odoo.http import request
from odoo.exceptions import Warning

import logging

_logger = logging.getLogger(__name__)


class FraktjaktStatus(http.Controller):

    @http.route('/webhook', type="json", auth="none", methods=['POST'])
    def get_order_status(self, **post):
        # Extract the payload from the POST request
        payload = request.get_json_data()

        _logger.info('Webhook payload: %s', payload)

        # Extract the order_id and status from the payload
        shipment_id = payload.get('shipment_id')
        order_status = payload.get('shipment_status')
        shipping_labels = payload.get('shipping_documents')
        attachment_ids = []

        if order_status == 'ready_to_ship':
            paid_order = request.env['stock.picking'].sudo().search([("fraktjakt_shipmentid", "=", shipment_id)])

            for url in shipping_labels:
                try:
                    # Download the PDF file from the URL
                    response = requests.get(url)
                    pdf_data = response.content

                    # Check if an attachment with the same name already exists
                    attachment = request.env['ir.attachment'].sudo().search([
                        ('name', '=', url.split('/')[-1]),
                        ('res_model', '=', 'stock.picking'),
                        ('res_id', '=', paid_order.id)
                    ])

                    if not attachment:
                        # Create a new attachment for the PDF file
                        attachment = request.env['ir.attachment'].sudo().create({
                            'name': url.split('/')[-1],
                            'type': 'binary',
                            'datas': base64.b64encode(pdf_data),
                            'res_model': 'stock.picking',
                            'res_id': paid_order.id,
                        })

                    attachment_ids.append(attachment.id)
                except Exception as e:
                    _logger.error('Error while creating attachment: %s', e)

        return request.make_json_response('[accepted]')
