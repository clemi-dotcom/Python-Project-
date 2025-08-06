from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import xmlrpc.client
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

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
    try:
        # Get incoming message and number
        message_body = request.form.get('Body', '')
        from_number = request.form.get('From', '')
        logging.info(f"Received SMS from {from_number}: {message_body}")

        if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]):
            logging.error("Missing one or more Odoo environment variables.")
            resp = MessagingResponse()
            resp.message("Server configuration error. Please try again later.")
            return str(resp)

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

        logging.info(f"Created Helpdesk ticket ID: {ticket_id}")

        # Twilio Response
        resp = MessagingResponse()
        resp.message("Thanks! We've opened a support ticket.")

    except Exception as e:
        logging.exception("Error processing incoming SMS.")
        resp = MessagingResponse()
        resp.message("Something went wrong while processing your message.")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
