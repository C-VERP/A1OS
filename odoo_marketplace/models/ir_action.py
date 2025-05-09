# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# License URL : https://store.webkul.com/license.html/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
import odoo
from odoo import models, fields, api, _
from odoo.exceptions import AccessError
import odoo.service.model as service_model
import logging
_logger = logging.getLogger(__name__)

SELLER_DOMAIN_STRING = "get_marketplace_seller_id()"


class IrActionWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def update_mp_dynamic_domain(self, res):
        """ Update domain for seller group"""
        if not res:
            return res
        obj_user = self.env.user
        try:
            for r in res:
                mp_dynamic_domain = r.get("domain", [])
                if mp_dynamic_domain and SELLER_DOMAIN_STRING in mp_dynamic_domain:
                    domain_list = eval(mp_dynamic_domain)
                    list_of_index = [index for index, mp_tuple in enumerate(domain_list) if SELLER_DOMAIN_STRING in str(mp_tuple[2])]
                    updated_domain = ""
                    if obj_user.has_group('odoo_marketplace.marketplace_officer_group'):
                        for index in list_of_index:
                            var = domain_list[index][0]
                            if var == "id":
                                domain_list.pop(index)
                            else:
                                domain_list[index] =  (var,'!=', False)
                        updated_domain = str(domain_list)
                    else:
                        seller_id = obj_user.partner_id.id
                        for index in list_of_index:
                            var = domain_list[index][0]
                            if var == "id":
                                r["view_mode"] = "form"
                                r["res_id"] = seller_id
                                r["views"] = [(self.env.ref('odoo_marketplace.wk_seller_form_view').id, "form")]
                            domain_list[index] =  (var,'in', [seller_id])
                        updated_domain = str(domain_list)
                    if SELLER_DOMAIN_STRING in (r.get('domain', '[]') or ''):
                        r['domain'] = updated_domain
        except Exception as e:
            _logger.warning("Warning !! Domain not found~%r",e)
            pass
        return res

    def read(self, fields=None, load='_classic_read'):
        res = super(IrActionWindow, self).read(fields=fields, load=load)
        return self.update_mp_dynamic_domain(res)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """ Method for frontend translation"""
        modules = super()._get_translation_frontend_modules_name()
        return modules + ['odoo_marketplace']

main_execute_kw = service_model.execute_kw

def new_execute_kw(db, uid, obj, method, args, kw=None):
    try:
        with odoo.registry(db).cursor() as cr:
            env = odoo.api.Environment(cr, uid, {})
            user = env['res.users'].browse(uid)
            if user.check_user_is_draft_or_approved_seller():
                raise AccessError('This operation is not allowed for marketplace sellers.')
        return main_execute_kw(db, uid, obj, method, args, kw)
    except Exception as e:
        _logger.error(f"Error{e}")
        raise

service_model.execute_kw = new_execute_kw
