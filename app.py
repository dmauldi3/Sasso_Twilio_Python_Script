from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv
import os
import stripe
import logging

# Load environment variables from .env
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up API keys from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
TECHNICIAN_NUMBER = os.getenv("TECHNICIAN_NUMBER")

# Flask app setup
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
        resp.say("Please leave a message after the tone.")
        resp.record(maxLength=60, action="/goodbye")
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


@app.route("/goodbye", methods=['POST'])
def goodbye():
    logging.info("Voicemail ended. Sending goodbye message.")
    resp = VoiceResponse()
    resp.say("Thank you. We’ll call you back soon.")
    resp.hangup()
    return Response(str(resp), mimetype='text/xml')


def has_active_subscription(phone_number):
    """Check if customer has active Stripe subscription using phone number as metadata"""
    try:
        customers = stripe.Customer.list(limit=100)
        for customer in customers.auto_paging_iter():
            if customer.get("phone") == phone_number:
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
from pyngrok import ngrok

if __name__ == "__main__":
    # Authenticate Ngrok with the token from your .env file
    NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
    if NGROK_AUTH_TOKEN:
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)

    # Open public tunnel on port 5000
    public_url = ngrok.connect(5000)
    logging.info(f"Ngrok tunnel started at {public_url}")
    logging.info("Paste this URL into your Twilio webhook: {public_url}/voice")

    # Start Flask server
    app.run(port=5000)
