from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import xmlrpc.client
import os
import logging
import requests
import base64

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Get Odoo credentials from environment variables
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

# Get Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

@app.route("/")
def home():
    return "Flask app is running!"

@app.route("/sms", methods=["POST"])
def sms_reply():
    try:
        message_body = request.form.get('Body', '')
        from_number = request.form.get('From', '')
        media_count = int(request.form.get('NumMedia', 0))
        logging.info(f"Received SMS from {from_number}: {message_body} with {media_count} media files")

        if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]):
            logging.error("Missing one or more Odoo environment variables.")
            resp = MessagingResponse()
            resp.message("Server configuration error. Please try again later.")
            return str(resp)

        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
            logging.error("Missing Twilio credentials in environment variables.")
            resp = MessagingResponse()
            resp.message("Server configuration error. Please try again later.")
            return str(resp)

        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

        # Build description including media URLs
        description = message_body
        if media_count > 0:
            description += "\n\nAttached Media URLs:"
            for i in range(media_count):
                media_url = request.form.get(f'MediaUrl{i}')
                content_type = request.form.get(f'MediaContentType{i}')
                description += f"\n- {media_url} ({content_type})"

        # Create Helpdesk Ticket
        ticket_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'helpdesk.ticket', 'create',
            [{
                'name': f'SMS from {from_number}',
                'description': description,
                'partner_phone': from_number,
                'team_id': 4  # Replace with your Helpdesk team ID
            }]
        )
        logging.info(f"Created Helpdesk ticket ID: {ticket_id}")

        # Download and attach media
        for i in range(media_count):
            media_url = request.form.get(f'MediaUrl{i}')
            media_type = request.form.get(f'MediaContentType{i}', 'application/octet-stream')

            if media_url:
                media_response = requests.get(
                    media_url,
                    auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                )
                if media_response.status_code == 200:
                    image_data = media_response.content
                    encoded_string = base64.b64encode(image_data).decode('utf-8')
                    filename = f'sms_attachment_{i}.{media_type.split("/")[-1]}'

                    attachment_id = models.execute_kw(
                        ODOO_DB, uid, ODOO_PASSWORD,
                        'ir.attachment', 'create',
                        [{
                            'name': filename,
                            'type': 'binary',
                            'datas': encoded_string,
                            'res_model': 'helpdesk.ticket',
                            'res_id': ticket_id,
                        }]
                    )
                    logging.info(f"Attached file {filename} to ticket {ticket_id}")
                else:
                    logging.warning(f"Failed to download media from {media_url} with status {media_response.status_code}")

        # Twilio confirmation
        resp = MessagingResponse()
        resp.message("Thanks! We've opened a support ticket with your message and attachment(s).")

    except Exception as e:
        logging.exception("Error processing incoming SMS.")
        resp = MessagingResponse()
        resp.message("Something went wrong while processing your message.")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
