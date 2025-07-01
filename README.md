# Twilio HubSpot Connector

A Flask-based application that integrates Twilio with HubSpot to handle incoming calls, forward them to technicians, and log call information in HubSpot CRM.

## Features

- **Call Forwarding**: Forwards incoming calls to one or more technician phone numbers
- **Call Logging**: Logs call details (duration, status, etc.) to HubSpot CRM
- **Contact Management**: Creates new contacts in HubSpot for unknown callers
- **Call Deduplication**: Prevents duplicate call records in HubSpot
- **Call Record Management**: Maintains a history of processed calls with automatic cleanup

## Requirements

- Python 3.7+
- Twilio account
- HubSpot account with API access
- Web server with public internet access (for Twilio webhooks)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/twilio-hubspot-connector.git
   cd twilio-hubspot-connector
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On macOS/Linux
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your configuration (see Configuration section below)

## Configuration

A `.env.example` file is provided in the repository as a template. Copy this file to create your own `.env` file:

```
cp .env.example .env
```

Then edit the `.env` file with your actual credentials:

```
TWILIO_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE=your_twilio_phone_number
TECHNICIAN_NUMBERS="+1234567890,+0987654321"  # Comma-separated list of phone numbers
HUBSPOT_API_KEY=your_hubspot_api_key
TWILIO_WEBHOOK_URL=your_public_webhook_url
```

Notes:
- Phone numbers should be in E.164 format (e.g., +1234567890)
- Multiple phone numbers (technician_numbers) should be separated by commas
- The webhook URL should be the public URL where your application is hosted, followed by `/voice`

## Usage

### Running Locally (Development)

```
python TwilioHubspotConnector.py
```

This will start the Flask application on `http://0.0.0.0:5000`.

For local development, you can use a tool like [ngrok](https://ngrok.com/) to create a public URL for testing:

```
ngrok http 5000
```

Update your Twilio phone number's voice webhook to the ngrok URL + `/voice`.

### Production Deployment

For production, it's recommended to use a WSGI server like Gunicorn:

```
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 TwilioHubspotConnector:app
```

You should also set up a reverse proxy (like Nginx) and configure SSL for secure connections.

## API Endpoints

### `/voice` (POST)
- **Purpose**: Handles incoming calls from Twilio
- **Functionality**: Forwards calls to technician numbers
- **Response**: TwiML instructions for Twilio

### `/call-status` (POST)
- **Purpose**: Receives call status updates from Twilio
- **Functionality**: Logs call status to HubSpot, especially for missed calls
- **Response**: Empty TwiML response

### `/call-completed` (POST)
- **Purpose**: Receives notification when a call is completed
- **Functionality**: Logs completed call details to HubSpot with duration
- **Response**: Simple "OK" response

## Call Flow

1. Caller dials the Twilio number
2. Twilio sends a webhook to `/voice`
3. The application instructs Twilio to forward the call to technician numbers
4. When the call status changes, Twilio sends a webhook to `/call-status`
5. When the call completes, Twilio sends a webhook to `/call-completed`
6. The application logs the call information to HubSpot at appropriate stages

## HubSpot Integration

The application integrates with HubSpot in the following ways:

1. **Contact Management**: Searches for existing contacts by phone number
2. **Contact Creation**: Creates new contacts for unknown callers
3. **Call Logging**: Creates call records associated with contacts
4. **Call Classification**: Classifies calls as "CONNECTED" or "NO_ANSWER" based on duration and status

## Maintenance

The application maintains a record of processed calls to prevent duplicates. These records are automatically cleaned up:

- On application startup
- Periodically after processing calls (every 10 calls)
- Records older than 7 days are removed
- Maximum of 100 call records are kept per phone number

## Troubleshooting

- **Logs**: The application logs information to the console with timestamps
- **Call Processing**: Check the `processed_calls.json` file to see which calls have been processed
- **HubSpot Integration**: Verify your HubSpot API key and check the application logs for API errors

## Security Considerations

- Keep your `.env` file secure and never commit it to version control
  - A `.gitignore` file is included in the repository that excludes the `.env` file
  - Always verify that your `.env` file is not being tracked before pushing changes
  - Use `git status` to confirm that `.env` is not listed in the tracked files
- The `.gitignore` file also excludes:
  - Private keys (*.pem files)
  - AWS-related configuration files
- Use `.env.example` as a template without including any real credentials
- Rotate your Twilio and HubSpot credentials periodically
- Use HTTPS for all production deployments
- Consider implementing IP restrictions for your webhooks in Twilio

**Warning**: Option 2 rewrites Git history and requires a force push, which can cause issues for collaborators. Make sure all team members are aware before proceeding.

## License

MIT License

Copyright (c) 2023 Your Organization

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
