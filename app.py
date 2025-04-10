from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv
import os
import stripe

# Load environment variables from .env
load_dotenv()

# Set up API keys from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
TECHNICIAN_NUMBER = os.getenv("TECHNICIAN_NUMBER")

# Flask app setup
app = Flask(__name__)


@app.route("/voice", methods=['POST'])
def voice():
    """Initial call handler"""
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
    resp = VoiceResponse()

    if digit_pressed == '1':
        if has_active_subscription(from_number):
            resp.say("Verifying your subscription. One moment.")
            resp.dial(TECHNICIAN_NUMBER)
        else:
            resp.say("No active subscription found.")
            resp.redirect('/voice')
    elif digit_pressed == '2':
        resp.say("Please leave a message after the tone.")
        resp.record(maxLength=60, action="/goodbye")
    elif digit_pressed == '3':
        send_payment_link(from_number)
        resp.say("A payment link has been sent via text. Thank you.")
        resp.hangup()
    else:
        resp.say("Invalid option.")
        resp.redirect('/voice')

    return Response(str(resp), mimetype='text/xml')


@app.route("/goodbye", methods=['POST'])
def goodbye():
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
                    return True
    except Exception as e:
        print(f"Stripe error: {e}")
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
    except Exception as e:
        print(f"Error sending payment link: {e}")
