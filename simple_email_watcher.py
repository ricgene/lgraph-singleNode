#!/usr/bin/env python3
"""
Simple Email Watcher with Duplicate Prevention
This is a simplified version that fixes the duplicate email issues.
"""

import imaplib
import email
import json
import time
import os
import requests
from email.header import decode_header
from datetime import datetime, timedelta
from simple_fix import SimpleConversationManager, process_email_simple

class SimpleEmailWatcher:
    """Simple email watcher with duplicate prevention"""
    
    def __init__(self):
        # Load configuration from environment
        self.gmail_user = os.getenv("GMAIL_USER")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        self.email_function_url = os.getenv("EMAIL_FUNCTION_URL")
        
        # Initialize conversation manager
        self.conversation_manager = SimpleConversationManager()
        self.conversation_manager.load_state()
        
        print(f"📧 Simple Email Watcher initialized")
        print(f"📧 Gmail User: {self.gmail_user}")
        print(f"📧 App Password length: {len(self.gmail_password) if self.gmail_password else 0}")
        print(f"📧 Email Function URL: {self.email_function_url}")
        
    def connect_to_gmail(self):
        """Connect to Gmail IMAP"""
        try:
            # Connect to Gmail IMAP server
            imap_server = "imap.gmail.com"
            imap = imaplib.IMAP4_SSL(imap_server)
            
            # Login
            imap.login(self.gmail_user, self.gmail_password)
            print(f"✅ Connected to Gmail IMAP")
            
            return imap
        except Exception as e:
            print(f"❌ Failed to connect to Gmail: {str(e)}")
            return None
    
    def search_for_prizm_emails(self, imap):
        """Search for new Prizm email replies"""
        try:
            # Select the INBOX
            imap.select("INBOX")
            
            # Search for unseen emails with "Re: Prizm Task Question" in subject
            search_criteria = [
                'UNSEEN',
                ['SUBJECT', 'Re: Prizm Task Question']
            ]
            
            # Get today's date for SINCE filter
            today = datetime.now().strftime("%d-%b-%Y")
            search_criteria.append(['SINCE', today])
            
            print(f"🔍 Searching for emails since {today}")
            print(f"🔍 Search criteria: {search_criteria}")
            
            # Search for emails
            status, message_numbers = imap.search(None, *search_criteria)
            
            if status != 'OK':
                print(f"❌ Search failed: {status}")
                return []
            
            if not message_numbers[0]:
                print("📭 No new Prizm email replies found")
                return []
            
            # Get message numbers
            message_list = message_numbers[0].split()
            print(f"📧 Found {len(message_list)} new Prizm email replies")
            
            return message_list
            
        except Exception as e:
            print(f"❌ Error searching for emails: {str(e)}")
            return []
    
    def extract_email_info(self, imap, message_num):
        """Extract email information"""
        try:
            # Fetch the email
            status, msg_data = imap.fetch(message_num, '(RFC822)')
            
            if status != 'OK':
                print(f"❌ Failed to fetch message {message_num}: {status}")
                return None
            
            # Parse the email
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Extract headers
            subject = decode_header(email_message["subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            
            from_header = decode_header(email_message["from"])[0][0]
            if isinstance(from_header, bytes):
                from_header = from_header.decode()
            
            # Extract email address from "Name <email@domain.com>" format
            user_email = from_header
            if '<' in from_header and '>' in from_header:
                user_email = from_header.split('<')[1].split('>')[0]
            
            # Extract email content
            email_content = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        email_content = part.get_payload(decode=True).decode()
                        break
            else:
                email_content = email_message.get_payload(decode=True).decode()
            
            # Create unique email ID
            email_id = f"{email_message['message-id']}-{int(time.time() * 1000)}-{user_email}-{subject}"
            
            return {
                "user_email": user_email,
                "subject": subject,
                "content": email_content.strip(),
                "email_id": email_id,
                "message_num": message_num
            }
            
        except Exception as e:
            print(f"❌ Error extracting email info: {str(e)}")
            return None
    
    def send_email_response(self, user_email, subject, body):
        """Send email response via GCP function"""
        try:
            payload = {
                "to": user_email,
                "subject": subject,
                "body": body
            }
            
            response = requests.post(self.email_function_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Email sent successfully: {subject}")
                return True
            else:
                print(f"❌ Failed to send email: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending email: {str(e)}")
            return False
    
    def process_emails(self):
        """Main email processing loop"""
        print("🔄 Starting email processing...")
        
        # Connect to Gmail
        imap = self.connect_to_gmail()
        if not imap:
            return
        
        try:
            # Search for new emails
            message_list = self.search_for_prizm_emails(imap)
            
            if not message_list:
                return
            
            # Process each email
            for message_num in message_list:
                print(f"\n📧 Processing message #{message_num.decode()}")
                
                # Extract email info
                email_info = self.extract_email_info(imap, message_num)
                if not email_info:
                    continue
                
                print(f"📧 Email ID: {email_info['email_id']}")
                print(f"📧 From: {email_info['user_email']}")
                print(f"📧 Subject: {email_info['subject']}")
                print(f"📧 Content: {email_info['content'][:100]}...")
                
                # Process the email using simple conversation manager
                result = process_email_simple(
                    email_info['user_email'],
                    email_info['content'],
                    email_info['email_id']
                )
                
                if result:
                    # Send email response if there's a question
                    if result.get('question') and not result.get('is_complete'):
                        email_body = f"""Hello!

Helen from Prizm here. I have a question for you about your task:

{result['question']}

Please reply to this email with your response.

Best regards,
Helen
Prizm Real Estate Concierge Service"""
                        
                        self.send_email_response(
                            email_info['user_email'],
                            f"Prizm Task Question",
                            email_body
                        )
                    
                    # Send completion email if conversation is complete
                    elif result.get('is_complete'):
                        completion_body = "Thank you for your time. We've completed our conversation about your task."
                        self.send_email_response(
                            email_info['user_email'],
                            "Prizm Task Conversation Complete",
                            completion_body
                        )
                
                print(f"✅ Processed email reply for: {email_info['user_email']}")
                
        except Exception as e:
            print(f"❌ Error processing emails: {str(e)}")
        
        finally:
            # Close connection
            imap.close()
            imap.logout()
            print("📧 IMAP connection closed")
    
    def run(self, check_interval=30):
        """Run the email watcher continuously"""
        print(f"🚀 Starting Simple Email Watcher (checking every {check_interval} seconds)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                self.process_emails()
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Email watcher stopped by user")
        except Exception as e:
            print(f"❌ Email watcher error: {str(e)}")

if __name__ == "__main__":
    # Set up environment variables for testing
    # Note: In production, these should be set via environment variables
    os.environ["EMAIL_FUNCTION_URL"] = "https://sendemail-cs64iuly6q-uc.a.run.app"
    
    watcher = SimpleEmailWatcher()
    watcher.run() 