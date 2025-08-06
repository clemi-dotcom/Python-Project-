from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

# Load environment variables (optional)
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

@app.route("/")
def index():
    return "Hello! Your SMS service is running."

@app.route("/sms", methods=["POST"])
def sms_reply():
    if request.method == "Post":
        return "This endpoint is for POST requests from Twilio. Nothing to see here."

    # Get the incoming message
    incoming_msg = request.form.get("Body")
    sender = request.form.get("From")

    # Create a Twilio response
    resp = MessagingResponse()
    msg = resp.message()

    # Example logic: Echo back the incoming message
    msg.body(f"Hello! You said: {incoming_msg}")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)

