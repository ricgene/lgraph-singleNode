const { markEmailContentProcessed, isEmailContentProcessed, enforceStrictThrottle, updateLastEmailSentTime } = require('./email_langgraph_integration.js');

// Test the new strict throttling and duplicate detection system
async function testStrictThrottleAndDuplicate() {
  console.log('🧪 Testing Strict Throttling and Duplicate Detection System\n');
  
  const testEmail = 'test@example.com';
  const testContent = 'This is a test email content';
  
  // Test 1: Mark content as processed
  console.log('Test 1: Marking email content as processed');
  markEmailContentProcessed(testEmail, testContent);
  
  // Test 2: Check if content is processed
  console.log('Test 2: Checking if content is processed');
  const isProcessed = isEmailContentProcessed(testEmail, testContent);
  console.log(`Is processed: ${isProcessed}`);
  
  // Test 3: Test strict throttling
  console.log('\nTest 3: Testing strict throttling');
  updateLastEmailSentTime(testEmail);
  
  // Try to send immediately
  const waitTime1 = enforceStrictThrottle(testEmail);
  console.log(`Wait time immediately after sending: ${waitTime1}ms`);
  
  // Wait 1 second and try again
  await new Promise(resolve => setTimeout(resolve, 1000));
  const waitTime2 = enforceStrictThrottle(testEmail);
  console.log(`Wait time after 1 second: ${waitTime2}ms`);
  
  // Wait 3 seconds and try again
  await new Promise(resolve => setTimeout(resolve, 2000));
  const waitTime3 = enforceStrictThrottle(testEmail);
  console.log(`Wait time after 3 seconds: ${waitTime3}ms`);
  
  // Test 4: Test different content
  console.log('\nTest 4: Testing different content');
  const differentContent = 'This is different content';
  const isDifferentProcessed = isEmailContentProcessed(testEmail, differentContent);
  console.log(`Is different content processed: ${isDifferentProcessed}`);
  
  // Test 5: Test multiple users
  console.log('\nTest 5: Testing multiple users');
  const user2 = 'user2@example.com';
  markEmailContentProcessed(user2, testContent);
  const isUser2Processed = isEmailContentProcessed(user2, testContent);
  const isUser1StillProcessed = isEmailContentProcessed(testEmail, testContent);
  console.log(`User 2 processed: ${isUser2Processed}`);
  console.log(`User 1 still processed: ${isUser1StillProcessed}`);
  
  console.log('\n✅ All tests completed!');
}

// Run the test
testStrictThrottleAndDuplicate().catch(console.error); 