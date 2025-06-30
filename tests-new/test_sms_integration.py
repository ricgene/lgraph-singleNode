#!/usr/bin/env python3
"""
SMS Integration Test
Tests the SMS webhook server and conversation flow
"""

import os
import json
import time
import requests
from datetime import datetime

# Test configuration
SMS_SERVER_URL = "http://localhost:5000"
TEST_PHONE_NUMBER = "+1234567890"

def test_sms_server_health():
    """Test if SMS server is running"""
    try:
        response = requests.get(f"{SMS_SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ SMS server is running")
            return True
        else:
            print(f"❌ SMS server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to SMS server: {e}")
        return False

def test_sms_status():
    """Get SMS server status"""
    try:
        response = requests.get(f"{SMS_SERVER_URL}/sms/status")
        if response.status_code == 200:
            status = response.json()
            print("📊 SMS Server Status:")
            print(f"  - Status: {status.get('status', 'unknown')}")
            print(f"  - Twilio configured: {status.get('twilio_configured', False)}")
            print(f"  - Mock mode: {status.get('mock_mode', True)}")
            print(f"  - Phone number: {status.get('phone_number', 'not set')}")
            print(f"  - Mock SMS count: {status.get('mock_sms_count', 0)}")
            return status
        else:
            print(f"❌ SMS status check failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ SMS status error: {e}")
        return None

def test_conversation_flow():
    """Test a complete SMS conversation flow"""
    print("\n🎬 Testing SMS conversation flow...")
    
    # Test conversation script
    conversation_script = [
        "",  # Initial greeting
        "Yes, I'm ready to discuss my task",
        "Yes, I'll reach out to the contractor",
        "No concerns, everything looks good"
    ]
    
    results = []
    
    for i, message in enumerate(conversation_script, 1):
        print(f"\n📱 Turn {i}: Sending '{message}'")
        
        try:
            response = requests.post(
                f"{SMS_SERVER_URL}/sms/mock",
                json={
                    "from": TEST_PHONE_NUMBER,
                    "message": message
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                conversation = result.get('conversation', {})
                
                print(f"🤖 Agent: {conversation.get('agent_response', 'No response')}")
                print(f"📊 Turn {conversation.get('turn_count', 0)} | Complete: {conversation.get('is_complete', False)}")
                
                results.append(result)
                
                # Stop if conversation is complete
                if conversation.get('is_complete', False):
                    print(f"🏁 Conversation completed after {i} turns")
                    break
                    
            else:
                print(f"❌ SMS request failed: {response.status_code}")
                break
                
        except Exception as e:
            print(f"❌ SMS test error: {e}")
            break
    
    return results

def test_manual_sms():
    """Test manual SMS sending"""
    print("\n📤 Testing manual SMS sending...")
    
    try:
        response = requests.post(
            f"{SMS_SERVER_URL}/sms/send",
            json={
                "to": TEST_PHONE_NUMBER,
                "message": "This is a test SMS from the webhook server!"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SMS sent successfully: {result.get('message', '')}")
            print(f"📧 SID: {result.get('sid', 'unknown')}")
            return True
        else:
            print(f"❌ Manual SMS failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Manual SMS error: {e}")
        return False

def test_performance():
    """Test SMS response performance"""
    print("\n⏱️ Testing SMS performance...")
    
    test_message = "Hello, I need help with my task"
    response_times = []
    
    for i in range(3):
        print(f"📊 Performance test {i+1}/3...")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{SMS_SERVER_URL}/sms/mock",
                json={
                    "from": f"+123456789{i}",
                    "message": test_message
                }
            )
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            if response.status_code == 200:
                print(f"✅ Response time: {response_time_ms:.2f}ms")
            else:
                print(f"❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Performance test error: {e}")
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"\n📊 Performance Summary:")
        print(f"  - Average: {avg_time:.2f}ms")
        print(f"  - Minimum: {min_time:.2f}ms")
        print(f"  - Maximum: {max_time:.2f}ms")
        
        return {"avg": avg_time, "min": min_time, "max": max_time}
    
    return None

def save_test_results(results):
    """Save test results to file"""
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"sms_test_results_{timestamp}.json")
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"📊 Test results saved to: {results_file}")
    return results_file

def main():
    """Run all SMS integration tests"""
    print("🚀 SMS Integration Test Suite")
    print("=" * 50)
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # Test 1: Server Health
    print("\n1️⃣ Testing server health...")
    health_ok = test_sms_server_health()
    test_results["tests"]["health"] = {"passed": health_ok}
    
    if not health_ok:
        print("❌ SMS server not running. Start it with: python sms_webhook_server.py")
        return
    
    # Test 2: Server Status
    print("\n2️⃣ Checking server status...")
    status = test_sms_status()
    test_results["tests"]["status"] = {"passed": status is not None, "data": status}
    
    # Test 3: Conversation Flow
    print("\n3️⃣ Testing conversation flow...")
    conversation_results = test_conversation_flow()
    test_results["tests"]["conversation"] = {
        "passed": len(conversation_results) > 0,
        "turns": len(conversation_results),
        "data": conversation_results
    }
    
    # Test 4: Manual SMS
    print("\n4️⃣ Testing manual SMS...")
    manual_sms_ok = test_manual_sms()
    test_results["tests"]["manual_sms"] = {"passed": manual_sms_ok}
    
    # Test 5: Performance
    print("\n5️⃣ Testing performance...")
    performance = test_performance()
    test_results["tests"]["performance"] = {
        "passed": performance is not None,
        "data": performance
    }
    
    # Save results
    results_file = save_test_results(test_results)
    
    # Summary
    passed_tests = sum(1 for test in test_results["tests"].values() if test["passed"])
    total_tests = len(test_results["tests"])
    
    print(f"\n🏁 Test Summary:")
    print(f"✅ Passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! SMS integration is working correctly.")
    else:
        print(f"⚠️ Some tests failed. Check the results file: {results_file}")

if __name__ == "__main__":
    main()