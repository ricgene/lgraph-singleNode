#!/usr/bin/env python3
"""
Simple Fix for Duplicate Email Issues
This script implements a simple solution to prevent duplicate emails and manage conversation state properly.
"""

import json
import os
import time
from datetime import datetime, timedelta

class SimpleConversationManager:
    """Simple conversation manager to prevent duplicates and manage state"""
    
    def __init__(self):
        self.conversations = {}  # user_email -> conversation_data
        self.processed_emails = set()  # Set of processed email IDs
        self.last_processed = {}  # user_email -> timestamp
        
    def should_process_email(self, user_email, email_content, email_id=None):
        """Check if we should process this email"""
        
        # Check if this exact email was already processed
        if email_id and email_id in self.processed_emails:
            print(f"🚫 Email {email_id} already processed - skipping")
            return False
            
        # Check time-based deduplication (30 second window)
        if user_email in self.last_processed:
            time_diff = time.time() - self.last_processed[user_email]
            if time_diff < 30:  # 30 seconds
                print(f"🚫 User {user_email} processed recently ({time_diff:.1f}s ago) - skipping")
                return False
        
        return True
    
    def mark_email_processed(self, user_email, email_id=None):
        """Mark an email as processed"""
        if email_id:
            self.processed_emails.add(email_id)
        self.last_processed[user_email] = time.time()
        
    def get_conversation_state(self, user_email):
        """Get conversation state for a user"""
        return self.conversations.get(user_email, {
            "conversation_history": "",
            "is_complete": False,
            "user_email": user_email,
            "turn_count": 0
        })
        
    def update_conversation_state(self, user_email, new_state):
        """Update conversation state for a user"""
        self.conversations[user_email] = new_state
        
    def save_state(self):
        """Save state to files"""
        # Save conversation states
        with open("simple_conversation_states.json", "w") as f:
            json.dump(self.conversations, f, indent=2)
            
        # Save processed emails
        with open("simple_processed_emails.json", "w") as f:
            json.dump(list(self.processed_emails), f, indent=2)
            
    def load_state(self):
        """Load state from files"""
        try:
            if os.path.exists("simple_conversation_states.json"):
                with open("simple_conversation_states.json", "r") as f:
                    self.conversations = json.load(f)
                    
            if os.path.exists("simple_processed_emails.json"):
                with open("simple_processed_emails.json", "r") as f:
                    self.processed_emails = set(json.load(f))
        except Exception as e:
            print(f"Warning: Could not load state: {e}")

# Global conversation manager
conversation_manager = SimpleConversationManager()

def process_email_simple(user_email, email_content, email_id=None):
    """Simple email processing function"""
    
    print(f"📧 Processing email from {user_email}")
    print(f"📝 Content: {email_content[:100]}...")
    
    # Check if we should process this email
    if not conversation_manager.should_process_email(user_email, email_content, email_id):
        return None
    
    # Get current conversation state
    current_state = conversation_manager.get_conversation_state(user_email)
    
    # Import the process_message function
    from oneNodeRemMem import process_message
    
    # Process the message
    result = process_message({
        "user_input": email_content,
        "previous_state": current_state,
        "user_email": user_email
    })
    
    # Update conversation state
    conversation_manager.update_conversation_state(user_email, {
        "conversation_history": result["conversation_history"],
        "is_complete": result["is_complete"],
        "user_email": user_email,
        "turn_count": result.get("turn_count", 0)
    })
    
    # Mark email as processed
    conversation_manager.mark_email_processed(user_email, email_id)
    
    # Save state
    conversation_manager.save_state()
    
    print(f"✅ Email processed successfully")
    print(f"📊 New state: {result['is_complete']}")
    print(f"💬 Response: {result['question'][:100]}...")
    
    return result

def test_simple_conversation():
    """Test the simple conversation manager"""
    print("🧪 Testing Simple Conversation Manager")
    print("=" * 50)
    
    # Initialize manager
    manager = SimpleConversationManager()
    
    # Test 1: First email from user
    print("\n📧 Test 1: First email from user")
    user_email = "test@example.com"
    email_content = "Yes, I am ready to discuss my task"
    email_id = "test-email-1"
    
    should_process = manager.should_process_email(user_email, email_content, email_id)
    print(f"Should process: {should_process}")
    
    if should_process:
        result = process_email_simple(user_email, email_content, manager)
        print(f"Response: {result}")
    
    # Test 2: Duplicate email (should be skipped)
    print("\n📧 Test 2: Duplicate email (should be skipped)")
    should_process = manager.should_process_email(user_email, email_content, email_id)
    print(f"Should process: {should_process}")
    
    # Test 3: New email from same user within 30 seconds (should be skipped)
    print("\n📧 Test 3: New email from same user within 30 seconds")
    new_email_id = "test-email-2"
    should_process = manager.should_process_email(user_email, "Another response", new_email_id)
    print(f"Should process: {should_process}")
    
    print("\n✅ Simple conversation manager test completed!")

if __name__ == "__main__":
    # Set up environment variables for testing
    # Note: In production, these should be set via environment variables
    os.environ["EMAIL_FUNCTION_URL"] = "https://sendemail-cs64iuly6q-uc.a.run.app"
    
    test_simple_conversation() 