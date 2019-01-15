# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
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
from odoo import models, fields, api, _
from odoo.exceptions import Warning
import requests
from requests.auth import HTTPBasicAuth
import json
import base64

import logging
_logger = logging.getLogger(__name__)


class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    unifaun_service_code = fields.Char('Service Code')
    is_unifaun = fields.Boolean('Is Unifaun')
    unifaun_sender = fields.Char(string='SenderPartners id', help="Code describing the carrier. See Unifaun help pages.")
    unifaun_customer_no = fields.Char(string='Customer Number', help="The paying party's customer number with the carrier.")
    #~ unifaun_environment = fields.Selection(string='Environment', selection=[('test', 'Test'), ('prod', 'Production')], default='test')

    #~ @api.multi
    #~ def test_environment(self):
        #~ self.ensure_one()
        #~ if 'test' in (self.env['ir.config_parameter'].get_param('unifaun.environment', 'prod'), self.unifaun_environment):
            #~ return True
        #~ return False

    def unifaun_download(self, url):
        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
        return self.env['ir.attachment'].create({
            'type': 'binary',
            'name': 'Unifaun pdf %s' %url.split("/")[-1],
            'datas': base64.b64encode(response.content),
        })

    def unifaun_send(self, method, params=None, payload=None):
        headers = {'content-type': 'application/json'}

        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        url = self.env['ir.config_parameter'].get_param('unifaun.url')

        response = requests.post(
            url + '/' + method,
            params=params,
            data=payload and json.dumps(payload) or None,
            headers=headers,
            verify=False,
            auth=HTTPBasicAuth(username, password))

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}

        return response.json()

    def unifaun_receive(self, method, params=None):
        headers = {'content-type': 'application/json'}

        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        url = self.env['ir.config_parameter'].get_param('unifaun.url')

        response = requests.get(
            url + '/' + method,
            params=params,
            headers=headers,
            verify=False,
            auth=HTTPBasicAuth(username, password))

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}

        return response.json()

    def get_file(self, url):
        username = self.env['ir.config_parameter'].get_param('unifaun.api_key')
        password = self.env['ir.config_parameter'].get_param('unifaun.passwd')
        response = requests.get(
            url,
            verify=False,
            auth=HTTPBasicAuth(username, password))
        if response.status_code < 200 or response.status_code >= 300:
            _logger.error("ERROR " + str(response.status_code) + ": " + response.text)
            return {'status_code': response.status_code,'text': response.text,'response': response}

        return response.content


class stock_picking_unifaun_status(models.Model):
    _name = 'stock.picking.unifaun.status'

    field = fields.Char(string='field')
    name = fields.Char(string='message')
    type = fields.Char(string='type')
    location = fields.Char(string='location')
    message_code = fields.Char(string='messageCode')
    raw_data = fields.Char(string='Raw Data')
    picking_id = fields.Many2one(comodel_name='stock.picking')


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    is_unifaun = fields.Boolean(related='carrier_id.is_unifaun')
    unifaun_shipmentid = fields.Char(string='Unifaun Shipment ID', copy=False)
    unifaun_stored_shipmentid = fields.Char(string='Unifaun Stored Shipment ID', copy=False)
    unifaun_package_code = fields.Char(string='Package Code', copy=False)
    unifaun_pdfs = fields.Char(string='Unifaun PDFs', copy=False)
    unifaun_status_ids = fields.One2many(comodel_name='stock.picking.unifaun.status', inverse_name='picking_id', string='Unifaun Status')

    # https://www.unifaunonline.se/rs-docs/
    # Create shipment to be completed manually
    # catch carrier_tracking_ref (to be mailed? add on waybill)

    @api.one
    def set_unifaun_status(self, statuses):
        if len(self.unifaun_status_ids) > 0:
            self.env['stock.picking.unifaun.status'].browse(self.unifaun_status_ids.mapped('id')).unlink()
        self.unifaun_status_ids = self.env['stock.picking.unifaun.status'].browse([])
        for d in statuses:
            self.env['stock.picking.unifaun.status'].create({
                'field': d.get('field'),
                'name': d.get('message'),
                'type': d.get('type'),
                'location': d.get('location'),
                'message_code': d.get('messageCode'),
                'raw_data': u'%s' %d,
                'picking_id': self.id,
            })
        # ~ {u'field': u'Party_CustNo', u'message': u'invalid check digit', u'type': u'error', u'location': u'', u'messageCode': u'Checkdigit'}

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
        receiver_contact = sender_contact = None
        if receiver.parent_id and receiver.type == 'contact':
            receiver_contact = receiver
            receiver = self.env['res.partner'].browse(receiver.parent_id.address_get(['delivery'])['delivery'])
        if sender.parent_id and sender.type == 'contact':
            sender_contact = sender
            sender = self.env['res.partner'].browse(sender.parent_id.address_get(['delivery'])['delivery'])
        if receiver.parent_id:
            if receiver.name:
                receiver_name = '%s, %s' % receiver.parent_id.name, receiver.name
            else:
                receiver_name = receiver.parent_id.name
        else:
            receiver_name = receiver.name
        rec = {
            'sender': {
                # ~ 'quickId': '1',
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
                'id': self.carrier_id.unifaun_sender or '',
                'custNo': self.carrier_id.unifaun_customer_no or '',
            }],
            'receiver': {
                'name': receiver_name,
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
                'id': self.carrier_id.unifaun_service_code or '',
            },
            'parcels':  [{
                'copies': self.number_of_packages or 1,
                'weight': self.weight or 0,
                'contents': _(self.env['ir.config_parameter'].get_param('unifaun.parcel_description', 'Goods')),
                'valuePerParcel': True,
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
        if sender_contact:
            rec['sender'].update({
                'phone': sender_contact.phone or sender_contact.mobile or '',
                'mobile': sender_contact.mobile or '',
                'email': sender_contact.email or '',
                'contact': sender_contact.name,
            })
        if receiver_contact:
            rec['receiver'].update({
                'phone': receiver_contact.phone or receiver_contact.mobile or '',
                'mobile': receiver_contact.mobile or '',
                'email': receiver_contact.email or '',
                'contact': receiver_contact.name,
            })

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
            self.set_unifaun_status(response.get('statuses') or [])
        else:
            self.env['mail.message'].create({
                'body': _("Unifaun error!<br/>rec %s<br/>resp %s<br/>" % (rec, response)),
                'subject': "Order Transport",
                'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                'res_id': self.id,
                'model': self._name,
                'type': 'notification',
            })
        _logger.info('Unifaun Order Transport: rec %s response %s' % (rec,response))

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
            # create an attachment
            # TODO: several pdfs?
            attachment = self.carrier_id.unifaun_download(unifaun_pdfs)
            attachment.write({
                'res_model': self._name,
                'res_id': self.id
            })
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
        _logger.info('Unifaun Order Transport: rec %s response %s' % (rec,response))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
