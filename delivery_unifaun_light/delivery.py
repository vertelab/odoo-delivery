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
    
    unifaun_sender = fields.Char(string='SenderPartners id', help="Code describing the carrier. See Unifaun help pages.")
    unifaun_customer_no = fields.Char(string='Customer Number', help="The paying party's customer number with the carrier.")

class stock_picking(models.Model):
    _inherit="stock.picking"
    
    is_unifaun = fields.Boolean(related='carrier_id.is_unifaun')
    unifaun_shipmentid = fields.Char(string='Unifaun Shipment ID', copy=False)
    unifaun_stored_shipmentid = fields.Char(string='Unifaun Stored Shipment ID', copy=False)
    unifaun_package_code = fields.Char(string='Package Code', copy=False)
    unifaun_pdfs = fields.Char(string='Unifaun PDFs', copy=False)
    
    # https://www.unifaunonline.se/rs-docs/
    # Create shipment to be completed manually
    # catch carrier_tracking_ref (to be mailed? add on waybill)
    
    @api.one
    def order_stored_shipment(self):
        """Create a stored shipment."""
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        if self.unifaun_stored_shipmentid:
            raise Warning(_('A stored shipment already exists for this order.'))
        #~ error = ''
        #~ #if not self.weight:
        #~ #    error += '\n' if error else ''
        #~ #    error += _('The delivery must have a weight.')
        #~ # TODO: Add more error handling
        #~ if error:
            #~ raise Warning(error)
        # Choose sender and receiver based on picking type (in or out).
        if self.picking_type_id.code == 'incoming':
            receiver = self.picking_type_id.warehouse_id.partner_id
            sender = self.partner_id
        elif self.picking_type_id.code == 'outgoing':
            sender = self.picking_type_id.warehouse_id.partner_id
            receiver = self.partner_id
        
        rec = {
            'sender': {
                #~ 'quickId': "1",
                'name': sender.name,
                'address1': sender.street or '',
                'address2': sender.street2 or '',
                'zipcode': sender.zip or '',
                'city': sender.city or '',
                'state': sender.state_id and sender.state_id.name or '',
                'country': sender.country_id and sender.country_id.code or '',
                'phone': sender.phone or sender.mobile or '',
                'mobile': sender.mobile or '',
                'email': sender.email or '',
            },
            'senderPartners': [{
                'id': self.carrier_id.unifaun_sender,
                'custNo': self.carrier_id.unifaun_customer_no,
            }],
            'receiver': {
                'name': receiver.name,
                'address1': receiver.street or '',
                'address2': receiver.street2 or '',
                'zipcode': receiver.zip or '',
                'city': receiver.city or '',
                'state': receiver.state_id and receiver.state_id.name or '',
                'country': sender.country_id and sender.country_id.code or '',
                'phone': receiver.phone or receiver.mobile or '',
                'mobile': receiver.mobile or '',
                'email': receiver.email or '',
            },
            'service': {
                'id': self.carrier_id.unifaun_service_code,
            },
            'parcels':  [{
                'copies': self.number_of_packages or 1,
                'weight': self.weight or 0,
                'contents': _(self.env['ir.config_parameter'].get_param('unifaun.parcel_description', 'Goods')),
                'valuePerParcel': False,
            }],
            'orderNo': self.name,
            'senderReference': self.origin,
            #~ "receiverReference": "receiver ref 345",
            #~ "options": [{
                #~ "message": "This is order number 123",
                #~ "to": "sales@unifaun.com",
                #~ "id": "ENOT",
                #~ "languageCode": "SE",
                #~ "from": "info@unifaun.com"
            #~ }],
        }
        
        response = self.carrier_id.unifaun_send('stored-shipments', None, rec)
        if type(response) == type({}):
            _logger.warn('\n%s\n' % response)
            self.unifaun_stored_shipmentid = response.get('id', '')
            
            self.env['mail.message'].create({
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.warn('Unifaun Order Transport: rec %s response %s' % (rec,response))
    
    @api.one
    def confirm_stored_shipment(self):
        """Create shipment(s) from a stored shipment."""
        if not self.unifaun_stored_shipmentid:
            raise Warning(_('No stored shipment found for this order.'))
        if self.unifaun_shipmentid:
            raise Warning(_('The stored shipment has already been confirmed (there is a Shipment id).'))
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        
        rec = {
          "target1Media": "laser-ste",
          "target1XOffset": 0.0,
          "target1YOffset": 0.0,
          "target2Media": "laser-a4",
          "target2XOffset": 0.0,
          "target2YOffset": 0.0,
          "target3Media": None,
          "target3XOffset": 0.0,
          "target3YOffset": 0.0,
          "target4Media": None,
          "target4XOffset": 0.0,
          "target4YOffset": 0.0
        }
        
        response = self.carrier_id.unifaun_send('stored-shipments/%s/shipments' % self.unifaun_stored_shipmentid, None, rec)
        if type(response) == type([]):
            _logger.warn('\n%s\n' % response)
            unifaun_shipmentid = ''
            carrier_tracking_ref = ''
            unifaun_pdfs = ''
            parcels = 0
            for r in response:
                # Could be more than one shipment.
                if carrier_tracking_ref:
                    carrier_tracking_ref += ', '
                carrier_tracking_ref += r.get('shipmentNo') or ''
                if unifaun_shipmentid:
                    unifaun_shipmentid += ', '
                unifaun_shipmentid += r.get('id') or ''
                for pdf in r.get('pdfs') or []:
                    if unifaun_pdfs:
                        unifaun_pdfs += ', '
                    unifaun_pdfs += pdf.get('href') or ''
                for parcel in r.get('parcels') or []:
                    parcels += 1
            self.number_of_packages = parcels
            self.carrier_tracking_ref = carrier_tracking_ref
            self.unifaun_shipmentid = unifaun_shipmentid
            self.unifaun_pdfs = unifaun_pdfs
            self.env['mail.message'].create({
                'body': _(u"Unifaun<br/>rec %s<br/>resp %s" % (rec, response)),
                'subject': "Shipment(s) Created",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s" % (rec, response)),
                'subject': "Create Shipment",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.warn('Unifaun Order Transport: rec %s response %s' % (rec,response))
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
