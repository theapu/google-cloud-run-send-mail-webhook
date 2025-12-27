import functions_framework
import os
import json
import base64
import hmac
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

@functions_framework.http
def send_email_webhook(request):
    """
    HTTP Cloud Function to send an email via Gmail API.
    Compatible with Watchtower/Shoutrrr generic JSON webhooks.
    """
    
    # --- 1. Authentication (Shared Secret) ---
    expected_secret = os.environ.get('WEBHOOK_SECRET')
    
    if expected_secret:
        # Check Header (Standard) OR Query Param (Watchtower URL)
        provided_secret = request.headers.get('X-Webhook-Secret') or request.args.get('secret')
        
        # Parse JSON early to check for secret in body if not found elsewhere
        raw_data = request.get_data(as_text=True)
        try:
            request_json = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            request_json = {}
        
        if not provided_secret:
            provided_secret = request_json.get('secret')

        if not provided_secret or not hmac.compare_digest(provided_secret, expected_secret):
             return json.dumps({'error': 'Unauthorized'}), 401, {'Content-Type': 'application/json'}
    else:
        raw_data = request.get_data(as_text=True)
        try:
            request_json = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            request_json = {}
    # -----------------------------------------

    # 2. Parse Data
    
    # Recipient: Defaults to environment variable since Watchtower doesn't send this
    recipient = request_json.get('recipient') or request.args.get('recipient') or os.environ.get('DEFAULT_RECIPIENT')
    
    # Subject: Use 'title' from JSON
    subject = request_json.get('title') or "Watchtower Notification"
    
    # Body: Use 'message' from JSON
    body = request_json.get('message') or "No content provided."

    # --- FIX: Handle Nested JSON (Double Encoding) ---
    # Watchtower templates often result in a JSON string being sent as the 'message'.
    # e.g. "{\"title\":\"Watchtower\",\"message\":\"...\"}"
    try:
        if isinstance(body, str) and body.strip().startswith('{'):
            potential_json = json.loads(body)
            # If we successfully parsed it and it has a 'message' field, extract it.
            if isinstance(potential_json, dict) and 'message' in potential_json:
                body = potential_json['message']
                # Optionally update title if present in the inner JSON
                if 'title' in potential_json:
                    subject = potential_json['title']
    except Exception:
        # If parsing fails, just use the original body string
        pass
    # -------------------------------------------------

    if not recipient:
        return 'Missing required field: recipient (and no DEFAULT_RECIPIENT env var set)', 400

    try:
        # 3. Authenticate using environment variables
        # FIX: Removed 'scopes' argument to prevent "invalid_scope" errors during refresh.
        # The refresh token itself already contains the authorized scopes.
        creds = Credentials(
            token=os.environ.get('ACCESS_TOKEN'),
            refresh_token=os.environ.get('REFRESH_TOKEN'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get('CLIENT_ID'),
            client_secret=os.environ.get('CLIENT_SECRET')
        )

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

        service = build('gmail', 'v1', credentials=creds)

        # 4. Create and Send Email
        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        message_body = {'raw': raw_message}

        sent_message = service.users().messages().send(userId='me', body=message_body).execute()
        
        return json.dumps({'message': 'Email sent', 'id': sent_message['id']}), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        print(f"Error sending email: {e}")
        return json.dumps({'error': str(e)}), 500, {'Content-Type': 'application/json'}