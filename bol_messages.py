from odoo import models, fields, api
import requests

class BolHelpdeskIntegration(models.Model):
    _name = 'bol.helpdesk.integration'
    _description = 'Importeer bol.com klantvragen naar Odoo Helpdesk'

    @api.model
    def import_bol_messages(self):
        client_id = self.env['ir.config_parameter'].sudo().get_param('bol.client_id')
        client_secret = self.env['ir.config_parameter'].sudo().get_param('bol.client_secret')

        token_response = requests.post(
            'https://login.bol.com/token',
            data={'grant_type': 'client_credentials'},
            auth=(client_id, client_secret)
        )
        token = token_response.json().get('access_token')

        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }

        response = requests.get(
            'https://api.bol.com/retailer/messages',
            headers=headers
        )
        messages = response.json().get('messages', [])

        HelpdeskTicket = self.env['helpdesk.ticket']

        for msg in messages:
            subject = msg.get('subject', 'Bol.com klantvraag')
            body = msg.get('body', '')
            customer_email = msg.get('customerEmail', 'onbekend@bol.com')

            HelpdeskTicket.create({
                'name': subject,
                'description': body,
                'partner_email': customer_email,
                'team_id': 1,
                'priority': '1',
            })
