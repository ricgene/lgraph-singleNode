import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import functions_framework
import json

def send_email_via_smtp(to_email, subject, body):
    """Send email using SMTP with Gmail app password"""
    try:
        # Get Gmail credentials from environment
        gmail_user = os.getenv('GMAIL_USER', 'foilboi808@gmail.com')
        gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not gmail_app_password:
            print("Error: GMAIL_APP_PASSWORD environment variable not set")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f'"Prizm Agent" <{gmail_user}>'
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'plain'))
        
        # Create SMTP session
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Login to the server
        server.login(gmail_user, gmail_app_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(gmail_user, to_email, text)
        server.quit()
        
        print(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@functions_framework.http
def send_email_simple(request):
    """HTTP Cloud Function for sending emails."""
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
    headers = {'Access-Control-Allow-Origin': '*'}

    try:
        # Parse the request
        request_json = request.get_json(silent=True)
        
        if not request_json:
            return ('No JSON data provided', 400, headers)
        
        # Extract email parameters
        to_email = request_json.get('to')
        subject = request_json.get('subject')
        body = request_json.get('body')
        
        if not all([to_email, subject, body]):
            return ('Missing required fields: to, subject, body', 400, headers)
        
        # Send the email
        success = send_email_via_smtp(to_email, subject, body)
        
        if success:
            return ('Email sent', 200, headers)
        else:
            return ('Failed to send email', 500, headers)
            
    except Exception as e:
        print(f"Error in send_email_simple: {e}")
        return (f'Error: {str(e)}', 500, headers) 