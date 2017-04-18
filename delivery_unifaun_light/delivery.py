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

class stock_picking(models.Model):
    _inherit="stock.picking"
    
    is_unifaun = fields.Boolean(related='carrier_id.is_unifaun')
    
    @api.one
    def order_transport(self):
        if self.carrier_tracking_ref:
            raise Warning(_('Transport already ordered (there is a Tracking ref)'))
        sender = self.picking_type_id.warehouse_id.partner_id
        rec = {
            'shipment': {
                'sender': {
                    #'quickId': "1",
                    'name': sender.name,        
                    'address1': sender.street,        
                    'zipcode': sender.zip,        
                    'city': sender.city,        
                    'country': sender.country_id.code,        
                    'phone': sender.phone,        
                    'email': sender.email,        
                },
                'receiver': {
                    'name': self.partner_id.name,        
                    'address1': self.partner_id.street,        
                    'zipcode': self.partner_id.zip,        
                    'city': self.partner_id.city,        
                    'country': self.partner_id.country_id.code,        
                    'phone': self.partner_id.phone,        
                    'email': self.partner_id.email,        
                },
                'service': {'id': self.carrier_id.unifaun_service_code,},
                'parcels':  [
                    {
                        "copies": 1,
                        "weight": self.weight,
                        #"contents": "Important stuff",
                        #"valuePerParcel": true
                    }],
        
                    },
                "orderNo": self.name,
                "senderReference": self.origin,
        }
        response = self.carrier_id.unifaun_receive('shipping',rec)
        self.carrier_tracking_ref = response.get('reference','')
        
        id = self.env['mail.message'].create({
                    'body': _("Unifaun\nrec %s\nresp %s\n" % (rec,response)),
                    'subject': "Order Transport",
                    'author_id': self.env['res.users'].browse(self.env.uid).partner_id.id,
                    'res_id': self.id,
                    'model': self._name,
                    'type': 'notification',})
        _logger.warn('Unifaun Order Transport: rec %s response %s' % (rec,response))
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
