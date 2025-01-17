# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID
from odoo.tools.sql import column_exists

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if column_exists(env.cr, "mk_instance", "analytic_account_id"):
        cr.execute("""alter table mk_instance add column temp_analytic_id int4""")
        cr.execute("""update mk_instance set temp_analytic_id = analytic_account_id""")

