#!/usr/bin/env python3
"""
Live Email Processing Test
This script simulates live email processing to test the duplicate detection system.
"""

import requests
import json
import time

def test_live_email_processing():
    """Test live email processing with duplicate detection"""
    print("🧪 Live Email Processing Test")
    print("=" * 50)
    
    server_url = "http://localhost:8000"
    
    # Test data - simulate real email content
    test_emails = [
        {
            "user_input": "Yes, I am ready to discuss my kitchen renovation task",
            "previous_state": None,
            "user_email": "test.user@example.com"
        },
        {
            "user_input": "Yes, I am ready to discuss my kitchen renovation task",  # Duplicate
            "previous_state": None,
            "user_email": "test.user@example.com"
        },
        {
            "user_input": "I want to renovate my kitchen cabinets and countertops",
            "previous_state": None,
            "user_email": "test.user@example.com"
        }
    ]
    
    print(f"📧 Testing with {len(test_emails)} emails")
    print(f"📧 User: {test_emails[0]['user_email']}")
    print(f"📧 Emails 1 & 2 have identical content (duplicate test)")
    print(f"📧 Email 3 has different content")
    
    results = []
    
    for i, email_data in enumerate(test_emails, 1):
        print(f"\n📧 Processing Email {i}")
        print("-" * 30)
        print(f"📝 Content: {email_data['user_input'][:50]}...")
        
        try:
            response = requests.post(f"{server_url}/process_message", json=email_data)
            
            if response.status_code == 200:
                result = response.json()
                results.append(result)
                
                print(f"✅ Response: {result.get('question', 'No question')[:50]}...")
                print(f"📊 State: {result.get('is_complete', False)}")
                
                # Check if this is a duplicate response
                if i > 1 and result.get('question') == results[i-2].get('question'):
                    print("⚠️  DUPLICATE RESPONSE DETECTED - Same as previous email")
                else:
                    print("✅ Unique response")
                    
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 30)
    print(f"📧 Total emails processed: {len(results)}")
    
    # Check for duplicates
    duplicate_responses = 0
    for i in range(1, len(results)):
        if results[i].get('question') == results[i-1].get('question'):
            duplicate_responses += 1
    
    print(f"🔄 Duplicate responses: {duplicate_responses}")
    
    if duplicate_responses > 0:
        print("⚠️  Duplicate responses detected - this may indicate:")
        print("   - Duplicate detection not working at server level")
        print("   - Or this is expected behavior for identical inputs")
    else:
        print("✅ No duplicate responses detected")
    
    print(f"\n✅ Live email processing test completed!")

if __name__ == "__main__":
    test_live_email_processing() 