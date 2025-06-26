#!/usr/bin/env python3
"""
Test script to simulate sending a Pub/Sub message from foilboi@gmail.com
to test the process-incoming-email workflow.
"""

import json
import base64
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_foilboi_workflow():
    """Test the workflow by simulating a Pub/Sub message from foilboi@gmail.com"""
    
    # Get the function URL from environment or use default
    function_url = os.getenv('PROCESS_EMAIL_FUNCTION_URL', 'http://localhost:8080')
    
    # Simulate the actual email body format from foilboi@gmail.com
    email_body = """CustomerName: Richard Genet,
    "custemail": richard.genet@gmail.com ,
    "Posted": empty,
    "DueDate": 6/27/2025, 12:00:00 AM,
    "Task": t 1035,
    "description": d,
    "Category": {Appraisal},
    "FullAddress": ,
    "Task Budget":1 ,
    "State": GA,
    "vendors": {I found three reputable vendors within 10 miles of the location who specialize in appraisals and have consistently high feedback ratings:

1. Best Appraisals LLC - Located at 123 Main Street, Anytown. With an average feedback rating of 4.9, Best Appraisals LLC has a proven track record of providing accurate and thorough appraisals in the area.

2. Elite Appraisal Services - Situated at 456 Oak Avenue, Nearby City. Elite Appraisal Services boasts an impressive average feedback rating of 4.8. Their team of experienced professionals is known for their attention to detail and timely service.

3. Superior Valuations Inc. - Found at 789 Elm Street, Local Town. Superior Valuations Inc. has an average feedback rating of 4.7. They are known for their comprehensive appraisal reports and commitment to customer satisfaction.

These vendors are well-regarded in the community and are equipped to handle the task with excellence. If you'd like, I can reach out to them with the task details for their approval.}"""
    
    # Simulate the Pub/Sub message data that would be sent by the email watcher
    message_data = {
        'userEmail': 'foilboi@gmail.com',
        'userResponse': email_body,
        'taskTitle': 'Prizm Task Question',
        'timestamp': '2024-01-15T10:30:00.000Z',
        'emailUid': 'test-email-123',
        'messageId': 'test-message-id-456',
        'subject': 'your new task'
    }
    
    print("🧪 Testing foilboi@gmail.com workflow with structured task data...")
    print(f"📤 Sending test message to: {function_url}")
    print(f"📧 From: {message_data['userEmail']}")
    print(f"📋 Task data preview: {email_body[:200]}...")
    
    try:
        # For HTTP testing, we'll send the message data directly
        # since the function also supports HTTP POST
        response = requests.post(
            f"{function_url}/process_email",
            json=message_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer test-token'  # You'll need a real Firebase token
            },
            timeout=30
        )
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Test completed successfully!")
        else:
            print("❌ Test failed!")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

def test_pubsub_message_format():
    """Test the Pub/Sub message format that would be sent by the email watcher"""
    
    print("\n📨 Testing Pub/Sub message format with structured task data...")
    
    # This is what the email watcher would send
    email_body = """CustomerName: Richard Genet,
    "custemail": richard.genet@gmail.com ,
    "Task": t 1035,
    "Category": {Appraisal},
    "State": GA"""
    
    message_data = {
        'userEmail': 'foilboi@gmail.com',
        'userResponse': email_body,
        'taskTitle': 'Prizm Task Question',
        'timestamp': '2024-01-15T10:30:00.000Z',
        'emailUid': 'test-email-123',
        'messageId': 'test-message-id-456'
    }
    
    # Encode as the email watcher would
    message_buffer = json.dumps(message_data).encode('utf-8')
    encoded_data = base64.b64encode(message_buffer).decode('utf-8')
    
    print(f"📤 Original message: {json.dumps(message_data, indent=2)}")
    print(f"📤 Encoded message: {encoded_data}")
    
    # Decode as the cloud function would
    decoded_data = base64.b64decode(encoded_data).decode('utf-8')
    decoded_message = json.loads(decoded_data)
    
    print(f"📥 Decoded message: {json.dumps(decoded_message, indent=2)}")
    
    if message_data == decoded_message:
        print("✅ Message encoding/decoding test passed!")
    else:
        print("❌ Message encoding/decoding test failed!")

def test_email_parsing():
    """Test the email parsing function"""
    
    print("\n🔍 Testing email parsing function...")
    
    # Test with the actual email format
    email_body = """CustomerName: Richard Genet,
    "custemail": richard.genet@gmail.com ,
    "Posted": empty,
    "DueDate": 6/27/2025, 12:00:00 AM,
    "Task": t 1035,
    "description": d,
    "Category": {Appraisal},
    "FullAddress": ,
    "Task Budget":1 ,
    "State": GA,
    "vendors": {I found three reputable vendors within 10 miles of the location who specialize in appraisals and have consistently high feedback ratings:

1. Best Appraisals LLC - Located at 123 Main Street, Anytown. With an average feedback rating of 4.9, Best Appraisals LLC has a proven track record of providing accurate and thorough appraisals in the area.

2. Elite Appraisal Services - Situated at 456 Oak Avenue, Nearby City. Elite Appraisal Services boasts an impressive average feedback rating of 4.8. Their team of experienced professionals is known for their attention to detail and timely service.

3. Superior Valuations Inc. - Found at 789 Elm Street, Local Town. Superior Valuations Inc. has an average feedback rating of 4.7. They are known for their comprehensive appraisal reports and commitment to customer satisfaction.

These vendors are well-regarded in the community and are equipped to handle the task with excellence. If you'd like, I can reach out to them with the task details for their approval.}"""
    
    print(f"📧 Test email body: {email_body[:200]}...")
    
    # Import the parsing function from the cloud function
    import sys
    import os
    sys.path.append('cloud_function')
    
    try:
        from main import parse_foilboi_email_body
        parsed_data = parse_foilboi_email_body(email_body)
        
        if parsed_data:
            print("✅ Email parsing successful!")
            print(f"📋 Parsed data: {json.dumps(parsed_data, indent=2)}")
            
            # Verify key fields
            expected_fields = ['CustomerName', 'custemail', 'Task', 'Category', 'State']
            for field in expected_fields:
                if field in parsed_data:
                    print(f"✅ Found {field}: {parsed_data[field]}")
                else:
                    print(f"❌ Missing {field}")
        else:
            print("❌ Email parsing failed!")
            
    except ImportError:
        print("⚠️ Could not import parsing function (cloud function not available)")
    except Exception as e:
        print(f"❌ Error testing email parsing: {e}")

if __name__ == "__main__":
    print("🚀 Starting foilboi@gmail.com workflow tests...\n")
    
    # Test the message format first
    test_pubsub_message_format()
    
    # Test email parsing
    test_email_parsing()
    
    # Test the actual workflow (requires deployed function)
    print("\n" + "="*50)
    test_foilboi_workflow()
    
    print("\n🎯 Test summary:")
    print("- Email watcher configured to accept emails from foilboi@gmail.com")
    print("- process_email_pubsub function added to handle Pub/Sub triggers")
    print("- Special parsing for structured task data from foilboi@gmail.com")
    print("- Workflow should now kick off properly for foilboi@gmail.com emails")
    print("- Task data will be parsed and stored in Firestore")
    print("- LangGraph will process the structured task request") 