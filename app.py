from flask import Flask, request, Response
import os
import xmlrpc.client

app = Flask(__name__)

# Load Odoo credentials from environment variables
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

# Authenticate with Odoo
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})

models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")


@app.route("/sms", methods=["POST"])
def sms_reply():
    from_number = request.form.get("From")
    message_body = request.form.get("Body")

    print(f"SMS received from {from_number}: {message_body}")

    # Create Helpdesk ticket in Odoo
    if uid:
        try:
            ticket_id = models.execute_kw(
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "helpdesk.ticket",
                "create",
                [{
                    "name": f"SMS from {from_number}",
                    "description": message_body,
                    "partner_phone": from_number,
                }]
            )
            print(f"Ticket created with ID: {ticket_id}")
        except Exception as e:
            print("Error creating ticket:", str(e))
    else:
        print("Failed to authenticate with Odoo")

    # Respond to Twilio with simple message
    response = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Message>Thanks! We've received your message.</Message>
    </Response>"""

    return Response(response, mimetype="text/xml")


if __name__ == "__main__":
    app.run(debug=True)

