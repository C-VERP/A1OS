# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
Added this file to inherit the account move class and added functions to send invoice and
refund invoice to amazon.
"""

import time
import base64
import logging
from odoo import fields, models, api, _
from odoo.addons.iap.tools import iap_tools
from ..endpoint import DEFAULT_ENDPOINT

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Inherited this class to store bill and shipping information into the account move
    so added custom fields  and store seller and instance information and selling info
    and amazon order ref.
    """
    _inherit = 'account.move'

    amazon_instance_id = fields.Many2one("amazon.instance.ept", "Marketplace")
    seller_id = fields.Many2one("amazon.seller.ept", "Seller")
    reimbursement_id = fields.Char()
    amz_fulfillment_by = fields.Selection([('FBA', 'Amazon Fulfillment Network'),
                                           ('FBM', 'Merchant Fulfillment Network')], string="Fulfillment By",
                                          help="Fulfillment Center by Amazon or Merchant")
    amz_sale_order_id = fields.Many2one("sale.order", string="Amazon Sale Order Id")
    feed_id = fields.Many2one("feed.submission.history", string="Feed Submission Id")
    ship_city = fields.Char(string="Ship City")
    ship_postal_code = fields.Char(string="Ship PostCode")
    ship_state_id = fields.Many2one("res.country.state", string='Ship State')
    ship_country_id = fields.Many2one('res.country', string='Ship Country')
    bill_city = fields.Char(string="Bill City")
    bill_postal_code = fields.Char(string="Bill PostCode")
    bill_state_id = fields.Many2one("res.country.state", string='Bill State')
    bill_country_id = fields.Many2one('res.country', string='Bill Country')
    invoice_url = fields.Char(string="Invoice URL")
    vcs_invoice_number = fields.Char(string='VCS Invoice Number')
    invoice_sent = fields.Boolean(string="Invoice Sent to Amazon?", default=False)
    is_undefined_amazon_returns = fields.Boolean(string="Undefined Amazon Returns?", default=False)

    @api.model_create_multi
    def create(self, vals_list):
        """ Check invoice_line_ids if False exist in the line then remove that line from list of
        invoice_line_ids this change is only for FBA Orders.
        @author: Keyur Kanani
        :param vals: invoice line dict
        :return:
        """
        for vals in vals_list:
            if self._context.get('default_move_type', {}) == 'out_invoice' and self._context.get('shipment_item_ids', {}):
                new_lines = []
                for inv_lines in vals.get('invoice_line_ids', []):
                    if inv_lines[2] and inv_lines[2].get('product_id', False):
                        new_lines.append(inv_lines)
                vals.update({'invoice_line_ids': new_lines})
            partner = self.env['res.partner'].browse(vals.get('partner_id', False))
            if partner.is_amz_customer:
                ship_partner = self.env['res.partner'].browse(vals.get('partner_shipping_id', False))
                order_ref = vals.get('amz_sale_order_id', '')
                sale_order_id = self.env['sale.order'].browse(order_ref)
                vals = self.amz_prepare_account_move_vals(vals, ship_partner, partner, sale_order_id)
        return super(AccountMove, self).create(vals_list)

    @staticmethod
    def amz_prepare_account_move_vals(vals, ship_partner, partner, sale_order_id):
        """
        Prepare values to extend in invoices.
        :param vals: dict{}
        :param ship_partner: res.partner()
        :param partner: res.partner()
        :param sale_order_id: sale.order()
        :return: vals{}
        """
        ship_state = ship_partner.state_id or sale_order_id.ship_state_id or False
        ship_country = ship_partner.country_id or sale_order_id.ship_country_id or False
        bill_state = partner.state_id or sale_order_id.bill_state_id or False
        bill_country = partner.country_id or sale_order_id.bill_country_id or False
        vals.update({
                'ship_city': ship_partner.city or sale_order_id.ship_city or '',
                'ship_postal_code': ship_partner.zip or sale_order_id.ship_postal_code or '',
                'ship_state_id': ship_state.id if ship_state else False,
                'ship_country_id': ship_country.id if ship_country else False,
                'bill_city': partner.city or sale_order_id.bill_city or '',
                'bill_postal_code': partner.zip or sale_order_id.bill_postal_code or '',
                'bill_state_id': bill_state.id if bill_state else False,
                'bill_country_id': bill_country.id if bill_country else False
        })
        return vals

    def request_upload_invoice_to_amazon(self, instance, shipped_orders_list):
        """
        This is method is used to upload the invoices to amazon and feed
        records will be created and invoice sent will mark as a True
        :param instance: amazon.instance.ept()
        :param shipped_orders_list: list()
        :return: True
        """
        after_req = 0.0
        invoice_ids = self.amz_sale_order_id.search(
            [('amz_order_reference', 'in', shipped_orders_list), ('amz_instance_id', '=', instance.id)]).mapped(
            'invoice_ids').filtered(lambda invoice: invoice.move_type in [
            'out_invoice', 'out_refund'] if instance.seller_id.amz_upload_refund_invoice else ['out_invoice'])
        for invoice_id in invoice_ids:
            kwargs = invoice_id._prepare_amz_invoice_upload_kwargs(instance)
            before_req = time.time()
            diff = int(after_req - before_req)
            if 3 > diff > 0:
                time.sleep(3 - diff)
            response = iap_tools.iap_jsonrpc(DEFAULT_ENDPOINT, params=kwargs, timeout=1000)
            after_req = time.time()
            self.process_invoice_feed_submission_response(response, instance, invoice_id.id)
        return True

    def get_amazon_shipped_order_list(self, instance, invoice_ids):
        """
        This method is used to check status of order which are shipped in amazon
        available invoice_ids and invoke the other method to upload the invoices.
        :param instance: amazon.instance.ept()
        :param invoice_ids: list()
        :return:  list()
        """
        invoice_ids = [invoice[0] for invoice in invoice_ids]
        orders_ids = self.browse(invoice_ids).mapped('amz_sale_order_id').mapped('amz_order_reference')
        kwargs = self.env['amazon.reports'].prepare_amazon_request_report_kwargs(instance.seller_id)
        kwargs.update({'emipro_api': 'get_amazon_orders_sp_api'})
        for x in range(0, len(orders_ids), 50):
            shipped_orders_list = []
            sale_orders_list = orders_ids[x:x + 50]
            sale_orders_list = ",".join(sale_orders_list)
            kwargs.update({'sale_order_list': sale_orders_list})
            response = iap_tools.iap_jsonrpc(DEFAULT_ENDPOINT, params=kwargs, timeout=1000)
            result = response.get('result', {}) if isinstance(response.get('result', {}), list) else [
                response.get('result', {})]
            for obj in result:
                orders = []
                orders = orders.append(obj.get('Orders', {})) if not isinstance(obj.get('Orders', []),
                                                                                list) else obj.get('Orders', [])
                [shipped_orders_list.append(order.get('AmazonOrderId')) for order in orders if
                 order.get('AmazonOrderId', False) and order.get('OrderStatus') == 'Shipped']
            self.request_upload_invoice_to_amazon(instance, shipped_orders_list)
        return True

    def upload_odoo_invoice_to_amazon(self, args={}):
        """ This method is used to upload odoo invoice to amazon
            :return: True """
        seller_obj = self.env['amazon.seller.ept']
        seller_id = args.get('seller_id', False)
        if not seller_id:
            _logger.info(_("Seller Id not found in Cron Argument, Please Check Cron Configurations."))
            return False
        seller = seller_obj.browse(seller_id)
        if seller.invoice_upload_policy != 'custom':
            _logger.info(_("Please Verify Invoice Upload Policy Configuration, from Seller Configuration Panel."))
            return False
        if seller.amz_upload_refund_invoice:
            refund_inv = "and move_type in ('out_invoice', 'out_refund')"
        else:
            refund_inv = "and move_type = 'out_invoice'"
        for instance in seller.instance_ids:
            query = """select id from account_move where amazon_instance_id=%s and state='posted' and 
            invoice_sent=False {refund_inv}""".format(refund_inv=refund_inv)
            self._cr.execute(query, (instance.id,))
            invoice_ids = self._cr.fetchall()
            self.get_amazon_shipped_order_list(instance, invoice_ids)
        return True

    def process_invoice_feed_submission_response(self, response, instance, invoice_id):
        """
        Process Amazon Feed Response for upload invoices to amazon
        :param response:
        :param instance:
        :param invoice_id:
        :return:
        """
        feed_submit_obj = self.env['feed.submission.history']
        if response.get('error', False):
            _logger.info(_(response.get('error', {})))
        results = response.get('results', {})
        if results.get('feed_result', {}).get('feedId', False):
            feed_document_id = results.get('result', {}).get('feedDocumentId', '')
            last_feed_submission_id = results.get('feed_result', {}).get('feedId', False)
            values = {'feed_result_id': last_feed_submission_id,
                      'feed_submit_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                      'instance_id': instance.id, 'user_id': self._uid,
                      'feed_type': 'upload_invoice',
                      'feed_document_id': feed_document_id,
                      'seller_id': instance.seller_id.id,
                      'invoice_id': invoice_id}
            feed = feed_submit_obj.create(values)
            invoice = self.browse(invoice_id)
            invoice.write({'invoice_sent': True, 'feed_id': feed.id})
            self._cr.commit()

    def _prepare_amz_invoice_upload_kwargs(self, instance):
        """
        Prepare arguments for submit invoice upload feed

        For Invoice:
        metadata:orderid=206-2341234-3455465;metadata:totalAmount=3.25;metadata:totalvatamount=1.23;
        metadata:invoicenumber=INT-3431-XJE3 OR
        metadata:shippingid=37fjxryfg3;metadata:totalAmount=3.25;metadata:totalvatamount=1.23;
        metadata:invoicenumber=INT-3431-XJE3

        For Credit Note:
        metadata:shippingid=283845474;metadata:totalAmount=3.25;metadata:totalvatamount=1.23;
        metadata:invoicenumber=INT-3431-XJE3;
        metadata:documenttype=CreditNote;metadata:transactionid=amzn:crow:429491192ksjfhe39sk

        @author: Keyur kanani
        :param invoice: account.move()
        :param instance: amazon.instance.ept()
        :return: feed values dict{}
        """
        report_obj = self.env['ir.actions.report']
        account = self.env['iap.account'].search([('service_name', '=', 'amazon_ept')])
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        metadata = {'metadata:orderid': self.amz_sale_order_id.amz_order_reference,
                    'metadata:totalamount': str(self.amount_total),
                    'metadata:totalvatamount': str(self.amount_tax),
                    'metadata:invoicenumber': self.name,
                    'metadata:documenttype': 'Invoice' if self.move_type == 'out_invoice' else 'CreditNote'}
        report_name = instance.seller_id.amz_invoice_report.report_name if instance.seller_id.amz_invoice_report else 'account.report_invoice'
        report = report_obj._get_report_from_name(report_name)
        result, result_type = report._render_qweb_pdf(report_name, res_ids=self.ids)
        invoice_pdf = base64.b64encode(result).decode('utf-8')
        return {'merchant_id': instance.seller_id.merchant_id and str(instance.seller_id.merchant_id) or False,
                'app_name': 'amazon_ept_spapi',
                'emipro_api': 'amazon_upload_vat_invoices_sp_api',
                'feed_type': 'UPLOAD_VAT_INVOICE',
                'account_token': account.account_token,
                'dbuuid': dbuuid,
                'data': invoice_pdf,
                'metadata': metadata,
                'amazon_marketplace_code': instance.country_id.amazon_marketplace_code or instance.country_id.code,
                'marketplaceids': [instance.market_place_id],
                }

    def _reconcile_reversed_moves(self, reverse_moves, move_reverse_cancel):
        """
        Inherited this method for force odoo default flow to skip reconciling refund invoices automatically.
        :param: reverse_moves: account.move()
        :param: move_reverse_cancel: True or False
        :return: account.move()
        """
        if self._context.get('amz_refund_invoice_ept', False):
            return reverse_moves
        super(AccountMove, self)._reconcile_reversed_moves(reverse_moves, move_reverse_cancel)
