from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bol_client_id = fields.Char("Bol.com Client ID", config_parameter="bol.client_id")
    bol_client_secret = fields.Char("Bol.com Client Secret", config_parameter="bol.client_secret")
