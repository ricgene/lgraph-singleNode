#!/usr/bin/env python3
import requests
import json

# Test with empty object as user_input
test_payload = {
  "user_input": {},
  "user_email": "test@example.com", 
  "task_json": {
    "taskId": "test_task_1",
    "userEmail": "test@example.com",
    "taskTitle": "Kitchen Renovation",
    "taskDescription": "Complete kitchen remodel",
    "taskType": "home_improvement",
    "createdAt": "2025-06-25T09:45:00",
    "status": "active",
    "agentStateKey": "taskAgent1_test@example.com_task_title_timestamp",
    "metadata": {
      "version": "1.0",
      "createdBy": "test",
      "lastUpdated": "2025-06-25T09:45:00"
    }
  },
  "previous_state": {
    "conversation_history": "",
    "is_complete": False,
    "user_email": "test@example.com"
  }
}

print("🧪 Testing with empty object {} as user_input")
print("=" * 50)

try:
    response = requests.post("http://localhost:8000/process_message", 
                           json=test_payload, 
                           headers={"Content-Type": "application/json"})
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Success! Agent response:")
        print(f"🤖 {result.get('question', 'No response')}")
        print(f"📊 Complete: {result.get('is_complete', False)}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}") 