from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import xmlrpc.client
import os
import logging
import requests
import base64

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Odoo credentials from environment
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

# Twilio credentials from environment
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

        if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
            logging.error("Missing one or more required environment variables.")
            resp = MessagingResponse()
            resp.message("Server configuration error. Please try again later.")
            return str(resp)

        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

        # Start ticket description with the message body only
        description = message_body

        # Create Helpdesk ticket
        ticket_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'helpdesk.ticket', 'create',
            [{
                'name': f'SMS from {from_number}',
                'description': description,
                'partner_phone': from_number,
                'team_id': 4  # replace with your actual helpdesk team ID
            }]
        )
        logging.info(f"Created Helpdesk ticket ID: {ticket_id}")

        # Download and attach media (and add embedded image if applicable)
        if media_count > 0:
            for i in range(media_count):
                media_url = request.form.get(f'MediaUrl{i}')
                media_type = request.form.get(f'MediaContentType{i}')
                media_response = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
                
                if media_response.status_code == 200:
                    image_data = media_response.content
                    logging.info(f"Downloaded media size: {len(image_data)} bytes")
                    
                    if len(image_data) == 0:
                        logging.warning(f"Downloaded media is empty for URL: {media_url}")
                        continue
                    
                    encoded_string = base64.b64encode(image_data).decode('utf-8')
                    file_extension = media_type.split("/")[-1]
                    filename = f'sms_attachment_{i}.{file_extension}'

                    # Create attachment in Odoo
                    attachment_id = models.execute_kw(
                        ODOO_DB, uid, ODOO_PASSWORD,
                        'ir.attachment', 'create',
                        [{
                            'name': filename,
                            'type': 'binary',
                            'datas': encoded_string,
                            'res_model': 'helpdesk.ticket',
                            'res_id': ticket_id,
                            'mimetype': media_type
                        }]
                    )
                    logging.info(f"Created attachment {attachment_id} for ticket {ticket_id}")

                    # Add <img> tag referencing the uploaded attachment
                    image_url = f"{ODOO_URL}/web/image/{attachment_id}?filename={filename}"
                    description += f'\n\n<img src="{image_url}" alt="{filename}" style="max-width: 300px;">'

                    # Update ticket description to include the embedded image
                    models.execute_kw(
                        ODOO_DB, uid, ODOO_PASSWORD,
                        'helpdesk.ticket', 'write',
                        [[ticket_id], {'description': description}]
                    )
                else:
                    logging.warning(f"Failed to download media from {media_url} with status {media_response.status_code}")

        # Respond to Twilio
        resp = MessagingResponse()
        resp.message("Thanks! We've opened a support ticket with your message and attachment(s).")

    except Exception as e:
        logging.exception("Error processing incoming SMS.")
        resp = MessagingResponse()
        resp.message("Something went wrong while processing your message.")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
