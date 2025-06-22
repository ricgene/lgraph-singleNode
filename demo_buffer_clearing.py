#!/usr/bin/env python3
"""
Demonstration of Email Buffer Clearing System
This script shows how the email buffer is cleared on startup and before sending emails.
"""

import json
import os
import time

def create_sample_buffer():
    """Create a sample email content buffer for demonstration"""
    sample_buffer = {
        "user1@example.com": [
            "hash1_old_email_content",
            "hash2_old_email_content", 
            "hash3_old_email_content"
        ],
        "user2@example.com": [
            "hash4_old_email_content",
            "hash5_old_email_content"
        ]
    }
    
    with open("email_content_buffer.json", "w") as f:
        json.dump(sample_buffer, f, indent=2)
    
    print("📝 Created sample email content buffer:")
    print(json.dumps(sample_buffer, indent=2))
    return sample_buffer

def simulate_server_startup():
    """Simulate server startup - clears the buffer"""
    print("\n🚀 Simulating Server Startup")
    print("=" * 40)
    
    if os.path.exists("email_content_buffer.json"):
        with open("email_content_buffer.json", "r") as f:
            old_buffer = json.load(f)
        print(f"📧 Found existing buffer with {sum(len(emails) for emails in old_buffer.values())} email hashes")
        
        # Clear the buffer (as done in main() function)
        os.remove("email_content_buffer.json")
        print("🗑️ Buffer cleared on startup")
        
        if not os.path.exists("email_content_buffer.json"):
            print("✅ Buffer file successfully removed")
        else:
            print("❌ Buffer file still exists")
    else:
        print("📧 No existing buffer found")

def simulate_email_processing():
    """Simulate processing emails and clearing buffer before sending"""
    print("\n📧 Simulating Email Processing")
    print("=" * 40)
    
    # Simulate receiving and processing an email
    user_email = "test@example.com"
    email_content = "Yes, I will call the contractor"
    
    print(f"📧 Processing email from: {user_email}")
    print(f"📝 Content: {email_content}")
    
    # Create new buffer with this email
    new_buffer = {
        user_email.lower().strip(): ["hash_of_processed_email"]
    }
    
    with open("email_content_buffer.json", "w") as f:
        json.dump(new_buffer, f, indent=2)
    
    print("📝 Added email to buffer")
    
    # Simulate clearing buffer before sending agent email
    print("\n📤 About to send agent email...")
    print("🗑️ Clearing buffer before sending (as requested)")
    
    if os.path.exists("email_content_buffer.json"):
        os.remove("email_content_buffer.json")
        print("✅ Buffer cleared before sending email")
    else:
        print("❌ Buffer file not found")
    
    # Simulate sending the email
    print("📤 Agent email sent!")
    print("📝 Buffer is now empty for next email")

def demonstrate_workflow():
    """Demonstrate the complete workflow"""
    print("🔄 Email Buffer Clearing Workflow Demonstration")
    print("=" * 60)
    
    # Step 1: Create sample buffer (simulating existing emails)
    sample_buffer = create_sample_buffer()
    
    # Step 2: Simulate server startup (clears buffer)
    simulate_server_startup()
    
    # Step 3: Simulate processing new emails
    simulate_email_processing()
    
    # Step 4: Show final state
    print("\n📊 Final State")
    print("=" * 20)
    if os.path.exists("email_content_buffer.json"):
        print("❌ Buffer file still exists (unexpected)")
    else:
        print("✅ Buffer file is cleared (expected)")
    
    print("\n✅ Workflow demonstration completed!")

if __name__ == "__main__":
    demonstrate_workflow() 