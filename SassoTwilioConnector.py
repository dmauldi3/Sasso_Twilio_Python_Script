from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv
import os
import stripe
import logging
import requests  # used to call Freshdesk

# Load environment variables from .env
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Twilio / Stripe / Freshdesk Credentials
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
TECHNICIAN_NUMBER = os.getenv("TECHNICIAN_NUMBER")

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")  # e.g. "mycompany.freshdesk.com"
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")  # see Profile settings in Freshdesk

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unhandled Exception: {e}", exc_info=True)
    return Response("An internal error occurred.", status=500)

@app.route("/voice", methods=['POST'])
def voice():
    """Initial call handler"""
    from_number = request.form.get('From')
    logging.info(f"Incoming call from {from_number}")

    resp = VoiceResponse()
    gather = Gather(num_digits=1, action='/menu', method='POST')
    gather.say("Welcome to Sasso support. Press 1 if you have a support subscription. "
               "Press 2 to leave a message. Press 3 to get a payment link.")
    resp.append(gather)
    resp.redirect('/voice')  # Repeat if no input
    return Response(str(resp), mimetype='text/xml')

@app.route("/menu", methods=['POST'])
def menu():
    """Handle menu selection"""
    digit_pressed = request.form.get('Digits')
    from_number = request.form.get('From')

    logging.info(f"User {from_number} pressed: {digit_pressed}")

    resp = VoiceResponse()

    if digit_pressed == '1':
        logging.info(f"Checking subscription for {from_number}")
        if has_active_subscription(from_number):
            logging.info(f"Subscription verified for {from_number}. Connecting to technician.")
            resp.say("Verifying your subscription. One moment.")
            resp.dial(TECHNICIAN_NUMBER)
        else:
            logging.info(f"No active subscription found for {from_number}")
            resp.say("No active subscription found.")
            resp.redirect('/voice')

    elif digit_pressed == '2':
        logging.info(f"{from_number} selected to leave a voicemail.")
        resp.say("Please leave a message after the tone. We'll create a support ticket from your voicemail.")
        resp.record(
            maxLength=60,
            action="/voicemail-freshdesk"
        )
        # Twilio ends the call or routes to /voicemail-freshdesk after recording

    elif digit_pressed == '3':
        logging.info(f"{from_number} requested a payment link.")
        send_payment_link(from_number)
        resp.say("A payment link has been sent via text. Thank you.")
        resp.hangup()

    else:
        logging.warning(f"{from_number} pressed an invalid option: {digit_pressed}")
        resp.say("Invalid option.")
        resp.redirect('/voice')

    return Response(str(resp), mimetype='text/xml')

@app.route("/voicemail-freshdesk", methods=['POST'])
def voicemail_freshdesk():
    """
    Twilio will POST here after recording the voicemail.
    We'll receive RecordingUrl, RecordingDuration, Caller phone, etc.
    Then create a Freshdesk ticket with that info.
    """
    recording_url = request.form.get('RecordingUrl')
    from_number = request.form.get('From') or "Unknown"
    call_sid = request.form.get('CallSid', 'N/A')
    duration = request.form.get('RecordingDuration', '0')

    logging.info(f"Voicemail ended. Creating Freshdesk ticket for {from_number}. RecordingUrl: {recording_url}")

    subject = f"New Voicemail from {from_number}"
    description = (
        f"Call SID: {call_sid}\n"
        f"Caller: {from_number}\n"
        f"Duration: {duration} seconds\n"
        f"Voicemail Recording: {recording_url}.mp3\n\n"
        "Please follow up with the caller."
    )

    create_freshdesk_ticket(subject, description)

    resp = VoiceResponse()
    resp.say("Thank you. We have created a support ticket from your voicemail. Goodbye.")
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')

def create_freshdesk_ticket(subject, description):
    """
    Calls Freshdesk API to create a ticket.
    Adjust fields as needed (priority, status, etc.).
    """
    freshdesk_url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets"

    ticket_data = {
        "subject": subject,
        "description": description,
        "email": "no-reply@sassousa-service.com",  # or a caller's email if known
        "priority": 1,  # 1=Low,2=Medium,3=High,4=Urgent
        "status": 2     # 2=Open,3=Pending,4=Resolved,5=Closed
    }

    headers = {
        "Content-Type": "application/json"
    }

    # Basic Auth with API key
    response = requests.post(
        freshdesk_url,
        headers=headers,
        json=ticket_data,
        auth=(FRESHDESK_API_KEY, "X")
    )

    if response.status_code == 201:
        logging.info("Freshdesk ticket created successfully.")
    else:
        logging.error(f"Failed to create Freshdesk ticket. Status code: {response.status_code}, Response: {response.text}")

def has_active_subscription(phone_number):
    """
    Checks if 'phone_number' belongs to any Stripe customer who has an active subscription.

    We compare both:
      1) main phone (customer.phone)
      2) a comma-separated list of additional phones in customer.metadata["additional_phones"].

    e.g. metadata = {"additional_phones": "+15551230001,+15551230002"}
    """
    try:
        customers = stripe.Customer.list(limit=100)
        for customer in customers.auto_paging_iter():
            # Main phone
            main_phone = (customer.get("phone") or "").strip()

            # Additional phones in metadata
            extra_phones_str = customer.get("metadata", {}).get("additional_phones", "")
            extra_phones = [p.strip() for p in extra_phones_str.split(",") if p.strip()]

            # If the caller's phone matches the main phone or any in the additional list
            if phone_number == main_phone or phone_number in extra_phones:
                # Check if there's any active subscription for that customer
                subs = stripe.Subscription.list(customer=customer.id, status="active")
                if subs.data:
                    logging.info(f"Active subscription found for {phone_number}")
                    return True

        logging.info(f"No active subscription found for {phone_number}")
    except Exception as e:
        logging.error(f"Stripe error checking subscription for {phone_number}: {e}")
    return False

def send_payment_link(phone_number):
    """Send a Stripe Checkout link via SMS using Twilio"""
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            success_url="https://yourdomain.com/success",
            cancel_url="https://yourdomain.com/cancel",
        )

        client.messages.create(
            to=phone_number,
            from_=TWILIO_PHONE,
            body=f"To get immediate support, subscribe here: {session.url}"
        )
        logging.info(f"Payment link sent to {phone_number}: {session.url}")
    except Exception as e:
        logging.error(f"Error sending payment link to {phone_number}: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
