# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)

class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"
    
    unifaun_sender = fields.Char(string='SenderPartners id')
    unifaun_customer_no = fields.Char(string='Customer Number')

class stock_picking(models.Model):
    _inherit="stock.picking"
    
    is_unifaun = fields.Boolean(related='carrier_id.is_unifaun')
    unifaun_shipmentid = fields.Char(string='Unifaun ID')
    
    # https://www.unifaunonline.se/rs-docs/
    # Create shipment to be completed manually
    # catch carrier_tracking_ref (to be mailed? add on waybill)
    
    @api.one
    def order_transport(self):
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        error = ''
        if not self.weight:
            error += '\n' if error else ''
            error += _('The delivery must have a weight.')
        #TODO: Add more error handling
        if error:
            raise Warning(error)
        sender = self.picking_type_id.warehouse_id.partner_id
        rec = {
            "pdfConfig": {
                "target4XOffset": 0,
                "target2YOffset": 0,
                "target1Media": "laser-ste",
                "target1YOffset": 0,
                "target3YOffset": 0,
                "target2Media": "laser-a4",
                "target4YOffset": 0,
                "target4Media": None,
                "target3XOffset": 0,
                "target3Media": None,
                "target1XOffset": 0,
                "target2XOffset": 0
            },
            'shipment': {
                'sender': {
                    'quickId': "1",
                    'name': sender.name,        
                    'address1': sender.street,        
                    'zipcode': sender.zip,        
                    'city': sender.city,        
                    'country': sender.country_id.code,        
                    'phone': sender.phone,        
                    'email': sender.email,        
                },
                "senderPartners": [{
                    "id": self.carrier_id.unifaun_sender,
                    "custNo": self.carrier_id.unifaun_customer_no,
                }],
                'receiver': {
                    'name': self.partner_id.name,        
                    'address1': self.partner_id.street,        
                    'zipcode': self.partner_id.zip,        
                    'city': self.partner_id.city,        
                    'country': self.partner_id.country_id.code,        
                    'phone': self.partner_id.phone,        
                    'email': self.partner_id.email,        
                },
                'service': {
                    'id': self.carrier_id.unifaun_service_code,
                },
                'parcels':  [{
                    "copies": 1,
                    "weight": self.weight,
                    "packageCode": "PC",
                    "contents": "Important stuff",
                    "valuePerParcel": True,
                }],
                "orderNo": self.name,
                "senderReference": self.origin,
                },
        }
        
        #~ if self.carrier_id.test_environment():
            #~ rec['shipment']['test'] = True
        response = self.carrier_id.unifaun_send('shipments', None, rec)
        if type(response) != type({}):
            for r in response:
                self.carrier_tracking_ref = r.get('shipmentNo', '')
                self.unifaun_shipmentid = r.get('id', '')
                for pdf in r.get('pdfs', []):
                    name = pdf.get('description', 'Unknown') + pdf.get('id', '001')
                    data = self.carrier_id.get_file(pdf.get('href', ''))
                    if type(data) != type({}):
                        self.env['ir.attachment'].create({
                            'name': name,
                            'datas_fname': name + '.pdf',
                            'data': data,
                            'res_model': self._name,
                            'res_id': self.id,
                            'description': 'Unifaun document.',
                        })
                    else:
                        self.env['mail.message'].create({
                            'body': _(u"Unifaun missing document\ndata %s" % data),
                            'subject': "Order Transport",
                            'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                            'res_id': self.id,
                            'model': self._name,
                            'type': 'notification',
                        })
        
            self.env['mail.message'].create({
                'body': _(u"Unifaun\nrec %s\nresp %s\n" % (rec, response)),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!\nrec %s\nresp %s\n" % (rec, response)),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.warn('Unifaun Order Transport: rec %s response %s' % (rec,response))
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
