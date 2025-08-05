from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import xmlrpc.client
import os

app = Flask(__name__)

# Get Odoo credentials from environment variables
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

@app.route("/")
def home():
    return "Flask app is running!"

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
            'team_id': 4  # Replace with your actual Helpdesk team ID
        }]
    )

    # Send confirmation back to user
    resp = MessagingResponse()
    resp.message("Thanks! We've received your message and opened a support ticket.")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
    # Send confirmation back to user
    resp = MessagingResponse()
    resp.message("Thanks! We've received your message and opened a support ticket.")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)

