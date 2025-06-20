from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Dial
from dotenv import load_dotenv
import os
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import re

# Create a session with retry capabilities
def create_requests_session(retries=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504, 429)):
    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Twilio / HubSpot Credentials
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
TECHNICIAN_NUMBERS = os.getenv("TECHNICIAN_NUMBERS", "")
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unhandled Exception: {e}", exc_info=True)
    return Response("An internal error occurred.", status=500)

@app.route("/", methods=['GET', 'POST'])
def debug():
    logging.info(f"Root endpoint accessed: {request.form}")
    return Response("Use /voice for Twilio.", status=200)

@app.route("/voice", methods=['POST'])
def voice():
    logging.info(f"Voice endpoint request: {request.form}")
    from_number = request.form.get('From')
    logging.info(f"Incoming call from {from_number}")

    if from_number:
        current_timestamp = int(time.time() * 1000)
        try:
            log_call_to_hubspot(from_number, 0, current_timestamp, "DIALING", "IN_PROGRESS")
        except Exception as e:
            logging.error(f"Error logging call to HubSpot: {str(e)}")

    resp = VoiceResponse()
    tech_numbers = [num.strip() for num in TECHNICIAN_NUMBERS.split(",") if num.strip()]
    if not tech_numbers or not all(re.match(r'^\+\d{10,15}$', num) for num in tech_numbers):
        logging.error("Invalid or empty technician numbers")
        return Response("Invalid technician numbers", status=500)

    dial = Dial(
        timeout=30,
        timeLimit=600,
        action="/call-status",
        method="POST"
    )
    for tn in tech_numbers:
        dial.number(
            tn,
            status_callback_event="completed",
            status_callback="/call-completed",
            status_callback_method="POST"
        )
    resp.append(dial)

    return Response(str(resp), mimetype='text/xml')

@app.route("/call-status", methods=['POST'])
def call_status():
    logging.info(f"Call-status endpoint request: {request.form}")
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('DialCallStatus')
    from_number = request.form.get('From')

    logging.info(f"Call status update for {call_sid} from {from_number}: {call_status}")
    if from_number and call_status:
        try:
            disposition = "CONNECTED" if call_status.lower() not in ["no-answer", "busy", "failed", "canceled"] else "NO_ANSWER"
            status = "COMPLETED" if disposition == "CONNECTED" else "MISSED"
            log_call_to_hubspot(from_number, 0, None, disposition, status)
            if disposition == "NO_ANSWER":
                logging.info(f"Logged missed call from {from_number} with status: {call_status}")
        except Exception as e:
            logging.error(f"Error logging missed call to HubSpot: {str(e)}")

    resp = VoiceResponse()
    return Response(str(resp), mimetype='text/xml')

@app.route("/call-completed", methods=['POST'])
def call_completed():
    logging.info(f"Call-completed endpoint request: {request.form}")
    call_sid = request.form.get('CallSid')
    from_number = request.form.get('From')
    call_duration = request.form.get('CallDuration', '0')
    call_status = request.form.get('CallStatus')

    logging.info(f"Call completed: {call_sid} from {from_number}, duration: {call_duration}s, status: {call_status}")
    if from_number:
        try:
            duration_seconds = int(call_duration) if call_duration.isdigit() else 0
            disposition = "CONNECTED" if duration_seconds > 0 and call_status.lower() not in ["busy", "failed", "no-answer", "canceled"] else "NO_ANSWER"
            status = "COMPLETED" if disposition == "CONNECTED" else "MISSED"
            log_call_to_hubspot(from_number, duration_seconds, None, disposition, status)
            logging.info(f"Updated call in HubSpot with duration: {duration_seconds}s, disposition: {disposition}")
        except Exception as e:
            logging.error(f"Error updating call in HubSpot: {str(e)}")

    return Response("OK", status=200)

def log_call_to_hubspot(caller_id, call_duration=0, call_timestamp=None, disposition="CONNECTED", status="COMPLETED"):
    if not HUBSPOT_API_KEY:
        logging.error("HubSpot API key not configured. Cannot log call.")
        return False

    call_duration_ms = int(call_duration) * 1000
    headers = {'Authorization': f'Bearer {HUBSPOT_API_KEY}', 'Content-Type': 'application/json'}
    session = create_requests_session(retries=3, backoff_factor=0.5)
    timeout = 10

    try:
        search_url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
        search_payload = {
            "filterGroups": [
                {
                    "filters": [
                        {"propertyName": "phone", "operator": "EQ", "value": caller_id}
                    ]
                },
                {
                    "filters": [
                        {"propertyName": "mobilephone", "operator": "EQ", "value": caller_id}
                    ]
                }
            ]
        }
        response = session.post(search_url, json=search_payload, headers=headers, timeout=timeout)

        contact_id = None
        if response.status_code == 200:
            search_results = response.json()
            contact_id = search_results.get('results', [{}])[0].get('id') if search_results.get('results') else None
            if not contact_id:
                create_url = "https://api.hubapi.com/crm/v3/objects/contacts"
                create_payload = {"properties": {"phone": caller_id, "firstname": "Unknown", "lastname": "Caller"}}
                create_response = session.post(create_url, json=create_payload, headers=headers, timeout=timeout)
                if create_response.status_code == 201:
                    contact_id = create_response.json().get('id')
                    logging.info(f"Created new contact: {contact_id}")
                else:
                    logging.error(f"Failed to create contact: {create_response.status_code} - {create_response.text}")
        else:
            logging.error(f"Contact search failed: {response.status_code} - {response.text}")

        if contact_id:
            call_timestamp = call_timestamp or int(time.time() * 1000)
            call_url = "https://api.hubapi.com/crm/v3/objects/calls"
            call_payload = {
                "properties": {
                    "hs_call_body": f"Incoming call from {caller_id}",
                    "hs_call_direction": "INBOUND",
                    "hs_call_disposition": disposition,
                    "hs_call_duration": str(call_duration_ms),
                    "hs_call_from_number": caller_id,
                    "hs_call_status": status,
                    "hs_timestamp": str(call_timestamp)
                },
                "associations": [{"to": {"id": contact_id}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 194}]}]
            }
            call_response = session.post(call_url, json=call_payload, headers=headers, timeout=timeout)
            if call_response.status_code == 201:
                logging.info(f"Successfully logged call to HubSpot for contact {contact_id}")
                return True
            else:
                logging.error(f"Failed to log call: {call_response.status_code} - {call_response.text}")
        else:
            logging.error("No contact ID available, cannot log call")
            return False

    except Exception as e:
        logging.error(f"Error in log_call_to_hubspot: {str(e)}")
        return False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
