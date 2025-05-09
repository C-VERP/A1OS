# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
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
{
  "name"                 :  "Odoo Multi Vendor Marketplace",
  "summary"              :  """Transform your business with Odoo's Multi Vendor Marketplace feature. Create and manage a marketplace with multiple vendors, allowing them to register, list products, manage orders, and track sales seamlessly. Enhance your marketplace operations and expand your product offerings with Odoo's powerful e-commerce solutions. Marketplace Management, Multi Vendor Platform Odoo, Vendor Registration, Product Listing, Order Management, Sales Tracking, Vendor Management, Marketplace Platform Odoo, Odoo E-commerce Solutions, sell on odoo marketplace, odoo marketplace, marketplace in Odoo, register sellers on marketplace, multi-seller marketplace, set up your own marketplace in odoo website, sellers marketplace in odoo, turn your odoo website in marketplace, how to set up seller marketplace in odoo, start marketplace in odoo, add multiple sellers, webkul marketplace""",
  "category"             :  "Website",
  "version"              :  "1.0.2",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-Multi-Vendor-Marketplace.html",
  "description"          :  """This functionality enables vendors to register, list their products, manage orders, and track sales within the Odoo system. It enhances the marketplace experience by providing a unified platform for vendors and buyers, improving operational efficiency and expanding the business's product offerings.""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=odoo_marketplace&lifetime=120&lout=1&custom_url=/",
  "depends"              :  [
                             'website_sale_stock',
                             'stock_account',
                             'delivery',
                             'sale_management',
                            ],
  "data"                 :  [
                             'security/marketplace_security.xml',
                             'edi/send_mail_to_seller.xml',
                             'edi/product_status_change_mail_to_admin.xml',
                             'edi/product_status_change_mail_to_seller.xml',
                             'edi/seller_creation_mail_to_admin.xml',
                             'edi/seller_creation_mail_to_seller.xml',
                             'edi/seller_status_change_mail_to_admin.xml',
                             'edi/seller_status_change_mail_to_seller.xml',
                             'edi/order_mail_to_seller.xml',
                             'data/mp_product_demo_data.xml',
                             'data/mp_config_setting_data.xml',
                             'data/seller_payment_method_data.xml',
                             'data/ir_config_parameter_data.xml',
                             'security/ir.model.access.csv',
                             'wizard/mark_approved.xml',
                             'wizard/publish.xml',
                             'wizard/unpublish.xml',
                             'wizard/server_action_wizard.xml',
                             'wizard/seller_status_reason_wizard_view.xml',
                             'wizard/seller_payment_wizard_view.xml',
                             'wizard/seller_registration_wizard_view.xml',
                             'wizard/variant_approval_wizard_view.xml',
                             'wizard/mark_done_stats.xml',
                             'views/sequence_view.xml',
                             'views/res_config_view.xml',
                             'views/website_config_view.xml',
                             'views/seller_shop_view.xml',
                             'views/res_partner_view.xml',
                             'views/seller_payment_view.xml',
                             'views/mp_stock_view.xml',
                             'views/seller_view.xml',
                             'views/mp_product_view.xml',
                             'views/mp_sol_view.xml',
                             'views/account_invoice_view.xml',
                             'views/seller_review_view.xml',
                             'views/website_mp_product_template.xml',
                             'views/website_mp_template.xml',
                             'views/website_seller_profile_template.xml',
                             'views/website_seller_shop_template.xml',
                             'views/website_account_template.xml',
                             'views/snippets/sell_snippets.xml',
                             'views/mp_menu_view.xml',
                             'data/marketplace_dashboard_demo.xml',
                             'data/seller_shop_style_data.xml',
                             'data/social_media_data.xml',
                             'views/mp_dashboard_view.xml',
                             'data/website_menus_data.xml',

                            ],
  "assets"              :  {
    "web.assets_backend" :  [
      'odoo_marketplace/static/src/css/mp_dashboard.css',
      'odoo_marketplace/static/src/xml/icon_restriction.xml',
      'odoo_marketplace/static/src/js/clickable_off.js',
      'odoo_marketplace/static/src/js/right_click_prevent.js',
    ],
    "web.assets_frontend" : [
      'odoo_marketplace/static/src/css/marketplace.css',
      'odoo_marketplace/static/src/css/marketplace_snippet.css',
      'odoo_marketplace/static/src/css/star-rating.css',
      'odoo_marketplace/static/src/css/review_chatter.scss',
      'odoo_marketplace/static/src/js/review_chatter.js',
      'odoo_marketplace/static/src/js/bootstrap-rating-input.min.js',
      'odoo_marketplace/static/src/js/star-rating.js',
      'odoo_marketplace/static/src/js/jquery.timeago.js',
      'odoo_marketplace/static/src/js/jquery.circlechart.js',
      'odoo_marketplace/static/src/js/seller_ratting.js',
      'odoo_marketplace/static/src/js/marketplace_snippets.js',
      'odoo_marketplace/static/src/js/marketplace.js',

    ]
  },
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  299,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
