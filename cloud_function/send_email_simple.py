import os
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import functions_framework
import json

def send_email_via_gmail(to_email, subject, body):
    """Send email using Gmail API"""
    try:
        # Get Gmail credentials from environment
        gmail_user = os.getenv('GMAIL_USER', 'foilboi808@gmail.com')
        
        # Create Gmail service
        service = build('gmail', 'v1')
        
        # Create message
        message = MIMEText(body)
        message['to'] = to_email
        message['from'] = gmail_user
        message['subject'] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send email
        sent_message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        
        print(f"✅ Email sent successfully to {to_email}")
        print(f"Message ID: {sent_message['id']}")
        return True
        
    except HttpError as error:
        print(f"❌ Gmail API error: {error}")
        return False
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False

@functions_framework.http
def send_email_simple(request):
    """HTTP Cloud Function to send emails"""
    # Set CORS headers for the preflight request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    try:
        # Parse request
        request_json = request.get_json()
        
        if not request_json:
            return ('No JSON data provided', 400, headers)
        
        to_email = request_json.get('to')
        subject = request_json.get('subject')
        body = request_json.get('body')
        
        if not all([to_email, subject, body]):
            return ('Missing required fields: to, subject, body', 400, headers)
        
        print(f"📧 Sending email to: {to_email}")
        print(f"📧 Subject: {subject}")
        print(f"📧 Body length: {len(body)} characters")
        
        # Send email
        success = send_email_via_gmail(to_email, subject, body)
        
        if success:
            return (json.dumps({'status': 'success', 'message': f'Email sent to {to_email}'}), 200, headers)
        else:
            return (json.dumps({'status': 'error', 'message': 'Failed to send email'}), 500, headers)
            
    except Exception as e:
        print(f"❌ Function error: {str(e)}")
        return (json.dumps({'status': 'error', 'message': str(e)}), 500, headers) 