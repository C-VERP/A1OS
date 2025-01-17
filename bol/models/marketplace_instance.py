import base64
import datetime
import json
import logging
import time

import requests

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.modules.module import get_module_resource

_logger_connection = logging.getLogger("Teqstars:bol.connection")

ACCOUNT_STATE = [('not_confirmed', 'Not Confirmed'), ('confirmed', 'Confirmed')]
ORDER_FILTER_STATUS = [('OPEN', 'OPEN'), ('SHIPPED', 'SHIPPED'), ('ALL', 'ALL')]


class MkInstance(models.Model):
    _inherit = "mk.instance"

    marketplace = fields.Selection(selection_add=[('bol', _("Bol.com"))], ondelete={'bol': 'set default'}, string='Marketplace')

    bol_client_id = fields.Char("Client ID", copy=False)
    bol_client_secret = fields.Char("Client Secret", copy=False)
    bol_access_token = fields.Char(string='Access Token', help='A rotatable unique token to access data from Bol', copy=False)
    bol_expires_in = fields.Char(string="Token Expired In", copy=False)
    bol_last_token_generated_on = fields.Datetime(string='Last Token Generated on', help='Use to automatic rotatable token if expired', copy=False)

    bol_operation_type = fields.Selection([('FBR', 'FBR'), ('FBB', 'FBB'), ('Both', 'FBR & FBB')], default="FBR", string="Use Operation For")
    bol_import_return = fields.Selection([('handled', 'Handled'), ('unhandled', 'Unhandled')], default="unhandled", string="Import Return for Status")

    bol_fbb_warehouse_id = fields.Many2one('stock.warehouse', string='FBB Warehouse', help="FBB order will go for into this warehouse.", ondelete='restrict', copy=False)

    bol_fbr_workflow_id = fields.Many2one("order.workflow.config.ts", "FBR Workflow", ondelete='restrict', copy=False)
    bol_fbb_workflow_id = fields.Many2one("order.workflow.config.ts", "FBB Workflow", ondelete='restrict', copy=False)

    bol_fbb_last_shipment_page_number = fields.Integer("FBB Shipment Page", copy=False,
                                                       help="Technical to manage pagination while importing shipped order/shipments. You can adjust it to zero if you wish to import shipped order from beginning (Past 90 days).")
    bol_fbr_last_shipment_page_number = fields.Integer("FBR Shipment Page", copy=False,
                                                       help="Technical to manage pagination while importing shipped order/shipments. You can adjust it to zero if you wish to import shipped order from beginning (Past 90 days).")
    bol_order_status = fields.Selection(ORDER_FILTER_STATUS, default='OPEN', string="Bol Order Status",
                                        help="To filter on order status. You can filter on either all orders independent from their status, open orders (excluding shipped and cancelled orders), and shipped orders.")

    bol_last_return_sync_on = fields.Datetime("Last Return Imported On", copy=False)
    bol_managing_excluded_taxes_on_product = fields.Boolean("Managing Excluded Taxes on Product?")
    bol_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', copy=False, ondelete='restrict')

    def bol_hide_instance_field(self):
        return ['last_customer_import_date', 'last_listing_import_date', 'is_update_odoo_product_category', 'is_sync_images', 'api_limit', 'discount_product_id', 'use_marketplace_currency', 'tax_system']

    def bol_hide_page(self):
        return ['description', 'product_images']

    @api.onchange('marketplace')
    def _onchange_bol_get_default_tax_system(self):
        if self.marketplace == 'bol':
            self.tax_system = 'default'

    def _get_bol_delivery_product(self):
        return self.env.ref('bol.bol_delivery', raise_if_not_found=False) or False

    def bol_mk_kanban_badge_color(self):
        return "#1000A4"

    def bol_mk_kanban_image(self):
        return get_module_resource('bol', 'static/description', 'bol_instance_icon.png')

    def bol_basic_auth(self):
        credentials = "%s:%s" % (self.bol_client_id, self.bol_client_secret)
        return base64.b64encode(credentials.encode('utf-8')).decode('utf-8').replace("\n", "")

    def bol_get_valid_fulfillment_options(self):
        self.ensure_one()
        valid_fulfillment_options = [self.bol_operation_type]
        if self.bol_operation_type == 'Both':
            valid_fulfillment_options = ['FBR', 'FBB']
        return valid_fulfillment_options

    @api.model
    def _send_bol_request(self, request_url, request_data, params={}, method='GET', accept='application/vnd.retailer.v10+json'):
        headers = {'Accept': accept}
        if accept == 'application/vnd.retailer.v10+json':
            headers.update({'Content-Type': 'application/vnd.retailer.v10+json'})
        if self.bol_access_token:
            validated = self.validate_bol_token_hash()
            if not validated:
                self.with_context(token_expired=True).bol_generate_new_token()
        if not self.bol_access_token:
            self.with_context(token_expired=True).bol_generate_new_token()
        if self.bol_access_token:
            headers.update({'Authorization': 'Bearer %s' % self.bol_access_token, })
        data = json.dumps(request_data) if request_data else False
        api_endpoint = 'https://api.bol.com/'
        api_url = api_endpoint + request_url
        try:
            _logger_connection.info('%s %s', method, api_url)
            if not data:
                req = requests.request(method, api_url, params=params, headers=headers)
            else:
                req = requests.request(method, api_url, data=data, params=params, headers=headers)
            if not self.env.context.get('from_queue'):
                req.raise_for_status()
            response_text = req.text
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                time.sleep(60)
                return self._send_bol_request(request_url, request_data, params=params, method=method, accept=accept)
            else:
                error_dict = e.response.json()
                error_detail = error_dict.get('detail')
                raise MarketplaceException(error_detail, f"{e.response.status_code} - {e.response.reason}")
        except Exception as e:
            raise MarketplaceException("%s" % req.text, additional_context={'show_traceback': True})
        _logger_connection.info('--> %d %s %db', req.status_code, req.reason, len(req.text))
        response = json.loads(response_text) if accept == 'application/vnd.retailer.v10+json' else response_text
        if isinstance(response, dict):
            if response.get('status') == 'FAILURE':
                raise MarketplaceException(_("{}: {}".format(response.get('eventType'), response.get('errorMessage'))))
        return response

    def validate_bol_token_hash(self):
        if self.bol_last_token_generated_on and self.bol_access_token and self.bol_expires_in is not None:
            delta = datetime.datetime.now() - self.bol_last_token_generated_on
            # duration = (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10 ** 6) / 10 ** 6
            if delta.total_seconds() > float(self.bol_expires_in):
                return False
            return True
        return False

    def bol_generate_new_token(self):
        self.ensure_one()
        if not self._context.get('token_expired', False):
            validated = self.validate_bol_token_hash()
            if validated:
                return True
        self.bol_access_token = False
        headers = {'Authorization': "Basic %s" % self.bol_basic_auth(), 'Accept': 'application/json'}
        try:
            req = requests.request("POST", "https://login.bol.com/token?grant_type=client_credentials", data={}, headers=headers)
            req.raise_for_status()
            response_text = req.text
        except requests.HTTPError as e:
            raise MarketplaceException(_("Bol API request failed with code: {}, msg: {}, content: {}".format(e.response.status_code, e.response.reason, e.response.content)))
        except Exception as e:
            raise MarketplaceException(_("%s" % e), additional_context={'show_traceback': True})
        response = json.loads(response_text)
        if response:
            self.bol_access_token = response.get('access_token')
            self.bol_expires_in = response.get('expires_in')
            self.bol_last_token_generated_on = datetime.datetime.now()
        self._cr.commit()
        return True

    def bol_action_confirm(self):
        if not self.bol_access_token:
            self.with_context(token_expired=True).bol_generate_new_token()
        self.set_pricelist('EUR')

    def reset_to_draft(self):
        return super(MkInstance, self).reset_to_draft()

    def bol_marketplace_operation_wizard(self):
        action = self.env.ref('base_marketplace.action_marketplace_operation').read()[0]
        action['views'] = [(self.env.ref('bol.bol_mk_operation_form_view').id, 'form')]
        return action

    def bol_setup_schedule_actions(self, mk_instance_id):
        cron_obj = self.env['ir.cron'].sudo()
        bol_cron_ids = self.env['ir.cron'].search([('mk_instance_id', '=', self.id), '|', ('active', '=', True), ('active', '=', False)])
        cron_list = [{'cron_name': 'Bol [{}] : Import FBR & FBB Order'.format(mk_instance_id.name), 'method_name': 'cron_auto_import_bol_orders', 'model_name': 'sale.order', 'interval_type': 'minutes', 'interval_number': 15},
                     {'cron_name': 'Bol [{}] : Export Order Status/Tracking Information to Bol'.format(mk_instance_id.name), 'method_name': 'cron_auto_update_bol_order_status', 'model_name': 'sale.order', 'interval_type': 'minutes',
                      'interval_number': 25},
                     {'cron_name': 'Bol [{}] : Import LVB/FBB Product\'s Stock'.format(mk_instance_id.name), 'method_name': 'cron_auto_import_fbb_bol_stock', 'model_name': 'mk.listing', 'interval_type': 'days', 'interval_number': 1},
                     {'cron_name': 'Bol [{}] : Export Product\'s Stock to Bol'.format(mk_instance_id.name), 'method_name': 'cron_auto_export_bol_stock', 'model_name': 'mk.listing', 'interval_type': 'minutes', 'interval_number': 25},
                     {'cron_name': 'Bol [{}] : Export Product\'s Price to Bol'.format(mk_instance_id.name), 'method_name': 'cron_auto_export_bol_price', 'model_name': 'mk.listing', 'interval_type': 'days', 'interval_number': 1},
                     {'cron_name': 'Bol [{}] : Import FBB Shipments For Open Order'.format(mk_instance_id.name), 'method_name': 'cron_auto_import_fbb_shipments', 'model_name': 'stock.picking', 'interval_type': 'hours', 'interval_number': 1},
                     {'cron_name': 'Bol [{}] : Import FBR Shipments For Open Order'.format(mk_instance_id.name), 'method_name': 'cron_auto_import_fbr_shipments', 'model_name': 'stock.picking', 'interval_type': 'hours', 'interval_number': 1},
                     {'cron_name': 'Bol [{}] : Import Returns'.format(mk_instance_id.name), 'method_name': 'cron_import_returns', 'model_name': 'bol.return', 'interval_type': 'hours', 'interval_number': 1}]
        for cron_dict in cron_list:
            bol_cron_ids -= cron_obj.create_marketplace_cron(mk_instance_id, cron_dict['cron_name'], method_name=cron_dict['method_name'], model_name=cron_dict['model_name'], interval_type=cron_dict['interval_type'], interval_number=cron_dict['interval_number'])
        if bol_cron_ids:
            bol_cron_ids.unlink()
        return True
