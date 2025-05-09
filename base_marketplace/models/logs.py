import logging
import datetime
from odoo import models, fields, api, _
from odoo.tools.misc import split_every
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger("Teqstars:Base Marketplace")


class MKLog(models.Model):
    _name = "mk.log"
    _description = "Marketplace Log"
    _order = 'write_date desc'

    name = fields.Char(string='Log Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade')
    log_line_ids = fields.One2many("mk.log.line", "log_id", "Log Lines")
    operation_type = fields.Selection([('import', 'Import'), ('export', 'Export'), ('webhook', 'Webhook')], string="Operation Type")
    log_message = fields.Text(related="log_line_ids.log_message")

    def prepare_create_line_vals(self, mk_log_line_dict, type):
        log_line_list = []
        mk_log_line_dict_ctx = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})  # Updating context will help to raise for any error.
        log_line_vals_list = mk_log_line_dict.get(type, [])
        log_line_vals_list = log_line_vals_list and [dict(t) for t in {tuple(d.items()) for d in log_line_vals_list}] or log_line_vals_list  # Remove duplicate key value dict.
        for log_dict in log_line_vals_list:
            log_dict.update({'state': type})
            log_line_list.append((0, 0, log_dict))
            mk_log_line_dict_ctx[type].append(log_dict)
        return log_line_list

    def create_update_log(self, mk_log_id=False, mk_instance_id=False, operation_type='', mk_log_line_dict=None):
        if not mk_instance_id and mk_log_id:
            mk_instance_id = mk_log_id.mk_instance_id
        log_line_list, log_level = [], mk_instance_id.log_level
        operation_type = self.env.context.get('operation_type', operation_type)
        marketplace_log_id = self.env.context.get('log_id', False) if not mk_log_id else mk_log_id
        mk_log_line_dict = mk_log_line_dict or self.env.context.get('mk_log_line_dict', {})
        if mk_log_line_dict:
            for log_type, log_list in mk_log_line_dict.items():
                _mk_logger = logging.getLogger("Teqstars:[{}]{}".format(mk_instance_id.marketplace, mk_instance_id.name))
                log_func = _mk_logger.error if log_type == 'error' else _mk_logger.info
                for log_data in log_list:
                    log_func(log_data.get('log_message'))
            if log_level == 'error':
                log_line_list.extend(self.prepare_create_line_vals(mk_log_line_dict, 'error'))
            if log_level == 'success':
                log_line_list.extend(self.prepare_create_line_vals(mk_log_line_dict, 'success'))
            if log_level == 'all':
                log_line_list.extend(self.prepare_create_line_vals(mk_log_line_dict, 'success'))
                log_line_list.extend(self.prepare_create_line_vals(mk_log_line_dict, 'error'))

        if not marketplace_log_id:
            log_vals = {'mk_instance_id': mk_instance_id and mk_instance_id.id or False, 'operation_type': operation_type}
            if log_line_list:
                log_vals.update({'log_line_ids': log_line_list})
            marketplace_log_id = self.create(log_vals)
        else:
            marketplace_log_id.write({'log_line_ids': log_line_list})
        return marketplace_log_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('mk.log') or _('New')
        return super().create(vals_list)

    @api.autovacuum
    def _do_log_clean(self):
        try:
            threshold = fields.Datetime().now() - relativedelta(days=10)
            self._cr.execute("SELECT id FROM mk_log WHERE create_date < %s", (threshold,))
            res = self._cr.fetchall()
            mk_log_ids = [res_id[0] for res_id in res]
            for mk_log_batch in split_every(200, mk_log_ids, piece_maker=tuple):
                self._cr.execute("DELETE FROM mk_log WHERE id IN %s", (tuple(mk_log_batch),))
        except Exception as e:
            _logger.error('Error while cleaning log: {} '.format(e))


class MKLogLine(models.Model):
    _name = "mk.log.line"
    _description = "Marketplace Log Line"
    _order = 'write_date desc'
    _rec_name = 'log_message'

    log_id = fields.Many2one("mk.log", "Log ID")
    state = fields.Selection([('error', 'Error'), ('success', 'Success')], string="Operation Status")
    log_message = fields.Text("Log Message")
    mk_instance_id = fields.Many2one('mk.instance', "Instance", related='log_id.mk_instance_id')
    queue_job_line_id = fields.Many2one("mk.queue.job.line", string="Queue Line")
