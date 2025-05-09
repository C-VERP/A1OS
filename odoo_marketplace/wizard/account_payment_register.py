from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_seller_payment = fields.Boolean("Seller Payment?")

    @api.depends('amount')
    def _compute_payment_difference(self):
        super(AccountPaymentRegister, self)._compute_payment_difference()
        if self._context.get("active_model", False) == "seller.payment" and self._context.get('active_id'):
            payable_amount = abs(self.env["seller.payment"].browse(self._context["active_id"]).payable_amount)
            for wizard in self:
                wizard.payment_difference = payable_amount - wizard.amount

    def _get_wizard_values_from_batch(self, batch_result):
        """Extract values from the batch passed as parameter to be mounted in the wizard view."""
        
        res = super(AccountPaymentRegister, self)._get_wizard_values_from_batch(batch_result)
        if self._context.get("active_model") == "account.move" and self._context.get('active_id'):
            invoice = self.env['account.move'].browse(self._context.get('active_id'))
            if invoice and invoice.is_seller and invoice.seller_payment_ids:
                res["is_seller_payment"] = True
                res["payment_type"] = "outbound"
        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)
        if self._context.get("active_model") == "account.move" and self._context.get('active_id'):
            invoice = self.env['account.move'].browse(self._context.get('active_id'))
            if invoice and invoice.is_seller and invoice.seller_payment_ids:
                res["is_seller_payment"] = True
                res["payment_type"] = "outbound"
        return res

    def action_create_payments(self):
        not_paid_invoices = self.env['account.move']
        if self._context.get('active_model') == 'account.move':
            invoice_ids = self.env['account.move'].browse(self._context.get('active_ids', []))
            not_paid_invoices = invoice_ids.filtered(lambda move: move.is_invoice(include_receipts=True) and move.payment_state not in ('paid', 'in_payment'))
        elif self._context.get('active_model') == 'account.move.line':
            invoice_ids = self.env['account.move.line'].browse(self._context.get('active_ids', []))
            if invoice_ids:
                invoice_ids = invoice_ids[0].move_id
            not_paid_invoices = invoice_ids.filtered(lambda move: move.is_invoice(include_receipts=True) and move.payment_state not in ('paid', 'in_payment'))
        res = super(AccountPaymentRegister, self).action_create_payments()
        not_paid_invoices.filtered(lambda move: move.payment_state in ('paid', 'in_payment')).mp_post_action_invoice_paid()
        return res
