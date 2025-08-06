import os
import logging
import requests
import base64
from flask import Flask, request, Response
import xmlrpc.client

# Configuration
ODOO_URL = os.environ.get('ODOO_URL', 'https://your-odoo-url.com')
ODOO_DB = os.environ.get('ODOO_DB', 'your_odoo_db')
ODOO_USERNAME = os.environ.get('ODOO_USERNAME', 'your_username')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'your_password')

# Logging setup
logging.basicConfig(level=logging.INFO)

# Odoo connection
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

# Flask app
app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
    return "Odoo SMS Integration is running!"

@app.route("/sms", methods=['POST'])
def sms():
    from_number = request.form.get('From')
    message_body = request.form.get('Body', '')
    media_count = int(request.form.get('NumMedia', 0))

    logging.info(f"Received SMS from {from_number}: {message_body} with {media_count} media files")

    # Construct initial ticket description
    description = f"<p><strong>SMS from {from_number}:</strong></p><p>{message_body}</p>"

    # Create helpdesk ticket
    ticket_id = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'helpdesk.ticket', 'create',
        [{
            'name': f'SMS from {from_number}',
            'description': description,
        }]
    )
    logging.info(f"Created Helpdesk ticket ID: {ticket_id}")

    # Download and attach media files to ticket as chatter messages
    for i in range(media_count):
        media_url = request.form.get(f'MediaUrl{i}')
        media_type = request.form.get(f'MediaContentType{i}', 'application/octet-stream')
        if media_url:
            media_response = requests.get(media_url)
            if media_response.status_code == 200:
                image_data = media_response.content
                encoded_data = base64.b64encode(image_data).decode('utf-8')
                filename = f'sms_attachment_{i}.{media_type.split("/")[-1]}'

                # Create attachment
                attachment_id = models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'ir.attachment', 'create',
                    [{
                        'name': filename,
                        'datas': encoded_data,
                        'datas_fname': filename,
                        'res_model': 'helpdesk.ticket',
                        'res_id': ticket_id,
                        'mimetype': media_type,
                    }]
                )

                # Post message with inline image in chatter
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'mail.message', 'create',
                    [{
                        'model': 'helpdesk.ticket',
                        'res_id': ticket_id,
                        'body': f"<p>Attached image: <img src='/web/image/{attachment_id}'/></p>",
                        'attachment_ids': [(4, attachment_id)],
                    }]
                )

                logging.info(f"Attached and posted file {filename} to ticket {ticket_id}")
            else:
                logging.warning(f"Failed to download media from {media_url}")

    return Response("<Response><Message>Ticket created successfully.</Message></Response>", mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
