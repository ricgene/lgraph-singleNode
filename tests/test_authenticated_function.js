#!/usr/bin/env node

/**
 * Test script for authenticated cloud function calls
 * This demonstrates how to call the process-incoming-email function with Firebase Authentication
 */

const axios = require('axios');

// Configuration
const FUNCTION_URL = 'https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email';
const TEST_USER_EMAIL = 'testuser@example.com';
const TEST_TASK_TITLE = 'Test Task with Auth';

// For testing purposes, we'll use a simple token
// In production, you would get this from Firebase Auth
const TEST_TOKEN = 'test-auth-token-12345';

async function testAuthenticatedFunction() {
  try {
    console.log('🧪 Testing authenticated cloud function...');
    console.log(`📧 Function URL: ${FUNCTION_URL}`);
    console.log(`👤 Test User: ${TEST_USER_EMAIL}`);
    console.log(`📋 Task Title: ${TEST_TASK_TITLE}`);
    
    const payload = {
      userEmail: TEST_USER_EMAIL,
      userResponse: 'This is a test message with Firebase Authentication.',
      taskTitle: TEST_TASK_TITLE
    };
    
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_TOKEN}`
    };
    
    console.log('\n📤 Sending authenticated request...');
    console.log('Headers:', JSON.stringify(headers, null, 2));
    console.log('Payload:', JSON.stringify(payload, null, 2));
    
    const response = await axios.post(FUNCTION_URL, payload, { headers });
    
    console.log('\n✅ Success!');
    console.log('Status:', response.status);
    console.log('Response:', JSON.stringify(response.data, null, 2));
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    
    if (error.response) {
      console.error('Status:', error.response.status);
      console.error('Response:', JSON.stringify(error.response.data, null, 2));
    }
  }
}

// Test without authentication (should fail)
async function testUnauthenticatedFunction() {
  try {
    console.log('\n🧪 Testing unauthenticated call (should fail)...');
    
    const payload = {
      userEmail: TEST_USER_EMAIL,
      userResponse: 'This should fail without auth.',
      taskTitle: TEST_TASK_TITLE
    };
    
    const headers = {
      'Content-Type': 'application/json'
      // No Authorization header
    };
    
    const response = await axios.post(FUNCTION_URL, payload, { headers });
    
    console.log('❌ Unexpected success! This should have failed.');
    console.log('Response:', response.data);
    
  } catch (error) {
    console.log('✅ Correctly failed without authentication');
    console.log('Status:', error.response?.status);
    console.log('Error:', error.response?.data?.message);
  }
}

// Run tests
async function runTests() {
  console.log('🚀 Starting Firebase Authentication Tests\n');
  
  await testUnauthenticatedFunction();
  await testAuthenticatedFunction();
  
  console.log('\n🏁 Tests completed!');
}

// Run if called directly
if (require.main === module) {
  runTests().catch(console.error);
}

module.exports = { testAuthenticatedFunction, testUnauthenticatedFunction }; 