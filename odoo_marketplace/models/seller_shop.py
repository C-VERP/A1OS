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

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID
import re

import logging
_logger = logging.getLogger(__name__)

class SellerShopStyle(models.Model):
    _name = "seller.shop.style"
    _description = "Seller Shop"

    name = fields.Char(string='Style Name', required=True)
    html_class = fields.Char(string='HTML Classes')


class SellerShop(models.Model):
    _name = 'seller.shop'
    _inherit = ['website.seo.metadata', 'website.published.mixin', 'mail.thread']
    _description = "Seller Shop"

    def _get_page_url(self):
        # For older version compatibility
        return None

    def _get_seller_products(self):
        # For older version compatibility
        return None

    def _get_page_new_url(self, url_handler):
        """ Compute shop url"""
        if url_handler:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url = base_url + "/seller/shop/"
            return base_url + url_handler

    def _get_seller_all_products(self, seller_id):
        """ Get seller all approved products"""
        if seller_id:
            product_objs = self.env["product.template"].search([('sale_ok', '=', True), (
                'status', '=', 'approved'), ("marketplace_seller_id", "=", seller_id)])
            if product_objs:
                return product_objs.ids
            else :
                return False

    def _default_website_sequence(self):
        self._cr.execute("SELECT MIN(website_sequence) FROM %s" % self._table)
        min_sequence = self._cr.fetchone()[0]
        return min_sequence and min_sequence - 1 or 10

    name = fields.Char(string="Shop Name",  translate=True, copy=False)
    shop_logo = fields.Binary(string="Image",
                              help="This field holds the image used as image for the product, limited to 1024x1024px.")
    shop_banner = fields.Binary(string="Shop Banner")
    description = fields.Text(string="Description",  translate=True)
    street = fields.Char(string='Street', copy=False)
    street2 = fields.Char(string='Street2', copy=False)
    zip = fields.Char(string='Zip', size=24, change_default=True, copy=False)
    city = fields.Char(string='City', copy=False)
    state_id = fields.Many2one(
        "res.country.state", string='State', ondelete='restrict', copy=False)
    country_id = fields.Many2one(
        'res.country', string='Country', ondelete='restrict', copy=False)
    email = fields.Char(string='Email', copy=False)
    phone = fields.Char(string='Phone', copy=False)
    fax = fields.Char(string='Fax', copy=False)
    shop_mobile = fields.Char(string="Mobile Number", copy=False)
    shop_tag_line = fields.Char(string="Tag Line", copy=False, size=100)
    seller_product_ids = fields.Many2many("product.template", string="Products")
    seller_id = fields.Many2one(
        "res.partner", string="Seller", domain="[('seller','=', True)]", required=True)
    sequence = fields.Integer(
        string='Sequence', help='Gives the sequence order when displaying a product list')
    active = fields.Boolean(
        'Active', default=True)
    state = fields.Selection([('new', 'New'), ('pending', 'Pending for Approval'), ('approved', 'Approved'), (
        'denied', 'Denied')], string="Shop Status", default="new", copy=False)
    color = fields.Integer(string="Color")
    shop_t_c = fields.Html(string="Terms & Conditions", copy=False)
    total_product = fields.Integer(string="Total Product")

    # Seller shop/profile releted field
    set_seller_wise_settings = fields.Boolean(string="Override default shop settings")

    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_style_ids = fields.Many2many('seller.shop.style', string='Styles')
    website_sequence = fields.Integer('Website Sequence', help="Determine the display order in the Website E-commerce",
                                      default=lambda self: self._default_website_sequence())
    website_ribbon_id = fields.Many2one('product.ribbon', string='Ribbon')
    url = fields.Char(string="URL")
    url_handler = fields.Char("Url Handler", required=True, help="Unique Shop URL handler...", copy=False)

    _sql_constraints = [('seller_id_uniqe', 'unique(seller_id)', _('This seller is already assign to another shop.')),
                        ('url_handler_unique', 'unique(url_handler)', _('Url Handler must be unique for the shop. Entered URL handler has been already used.')),
                        ('name_unique', 'unique(name)', _('Shop name has been already used. Shop name must be unique so change shop name.'))]

    @api.onchange('name')
    def on_change_name(self):
        """ Change url_handler on changing name"""
        if self.name and not self.url_handler:
            self.url_handler = self.name.lower().replace(' ', '-') or ""

    #CRUD Method
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            url_handler = vals.get('url_handler')
            seller_id = vals.get("seller_id")
            if url_handler:
                if not re.match('^[a-zA-Z0-9-_]+$', url_handler) or re.match('^[-_][a-zA-Z0-9-_]*$', url_handler) or re.match('^[a-zA-Z0-9-_]*[-_]$', url_handler):
                    raise UserError(_("Please enter URL handler correctly!"))
                vals["url"] = self._get_page_new_url(url_handler)
            if seller_id:
                seller_product_ids = self._get_seller_all_products(seller_id)
                vals.update({
                    "seller_product_ids": seller_product_ids,
                    "total_product": len(seller_product_ids) if seller_product_ids else 0
                })
        shop_ids = super(SellerShop, self).create(vals_list)
        for res in shop_ids:
            res.seller_id.seller_shop_id = res.id
            res.state = res.seller_id.state
        return shop_ids

    def write(self, vals):
        url_handler = vals.get('url_handler')
        seller_id = vals.get("seller_id")
        seller_obj = None
        if seller_id:
            seller_obj = self.env["res.partner"].browse(seller_id)
        for obj in self:
            if url_handler:
                if not re.match('^[a-zA-Z0-9-_]+$', url_handler) or re.match('^[-_][a-zA-Z0-9-_]*$', url_handler) or re.match('^[a-zA-Z0-9-_]*[-_]$', url_handler):
                    raise UserError(_("Please enter URL handler correctly!"))
                vals["url"] = self._get_page_new_url(url_handler)
            if seller_id:
                seller_product_ids = self._get_seller_all_products(seller_id)
                obj.seller_id.seller_shop_id = None
                vals.update({
                    "state": seller_obj.state,
                    "seller_product_ids": seller_product_ids,
                    "total_product":len(seller_product_ids) if seller_product_ids else 0
                })
        res = super(SellerShop, self).write(vals)
        if seller_id:
            for obj in self:
                seller_obj.write({"seller_shop_id": obj.id})
        elif vals.get('seller_product_ids'):
            for obj in self:
                obj.total_product = len(obj.seller_product_ids)

        return res

    def save(self):
        self.ensure_one()
        seller_obj = self.env["res.partner"].browse(self._context.get("active_id"))
        if seller_obj:
            seller_obj .write({"seller_shop_id": self.id})

    def seller_sales_count(self):
        """ Calculate seller total sales count"""
        sales_count = 0
        all_products = self.env['product.template'].sudo().search(
            [("marketplace_seller_id", "=", self.seller_id.sudo().id)])
        for prod in all_products.with_user(SUPERUSER_ID):
            sales_count += prod.sales_count
        return sales_count

    def _get_website_ribbon(self):
        return self.website_ribbon_id

    def set_sequence_top(self):
        self.website_sequence = self.sudo().search([], order='website_sequence desc', limit=1).website_sequence + 1

    def set_sequence_bottom(self):
        self.website_sequence = self.sudo().search([], order='website_sequence', limit=1).website_sequence - 1

    def set_sequence_up(self):
        previous_shop = self.sudo().search(
            [('website_sequence', '>', self.website_sequence), ('website_published', '=', self.website_published)],
            order='website_sequence', limit=1)
        if previous_shop:
            previous_shop.website_sequence, self.website_sequence = self.website_sequence, previous_shop.website_sequence
        else:
            self.set_sequence_top()

    def set_sequence_down(self):
        next_shop = self.search([('website_sequence', '<', self.website_sequence), ('website_published', '=', self.website_published)], order='website_sequence desc', limit=1)
        if next_shop:
            next_shop.website_sequence, self.website_sequence = self.website_sequence, next_shop.website_sequence
        else:
            return self.set_sequence_bottom()
