# app.py
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import xmlrpc.client

app = Flask(__name__)

# Odoo credentials
ODOO_URL = 'https://81hospitality.odoo.com'
ODOO_DB = 'https://81hospitality.odoo.com/odoo'
ODOO_USERNAME = 'clemi@81hospitality.com'
ODOO_PASSWORD = 'Admin@2024!'

@app.route("/sms", methods=["POST"])
def sms_reply():
    # Get incoming message and number
    message_body = request.form['Body']
    from_number = request.form['From']

    # Connect to Odoo
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    # Create Helpdesk Ticket
    ticket_id = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'helpdesk.ticket', 'create',
        [{
            'name': f'SMS from {from_number}',
            'description': message_body,
            'partner_phone': from_number,
            'team_id': 4  # Replace with your helpdesk team ID
        }]
    )

    # Send confirmation back to user
    resp = MessagingResponse()
    resp.message("Thanks! We've received your message and opened a support ticket.")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
