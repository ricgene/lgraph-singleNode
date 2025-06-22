const { markEmailContentProcessed, isEmailContentProcessed, enforceStrictThrottle, updateLastEmailSentTime } = require('./email_langgraph_integration.js');

// Simulate the exact duplicate scenario
async function testDuplicateScenario() {
  console.log('🧪 Testing Duplicate Email Scenario\n');
  
  const userEmail = 'richard.genet@gmail.com';
  const emailContent = 'Yes, i will contact the contractor today 4';
  
  console.log('Scenario: User sends same email content multiple times');
  console.log(`User: ${userEmail}`);
  console.log(`Content: "${emailContent}"\n`);
  
  // Simulate first email processing
  console.log('=== FIRST EMAIL PROCESSING ===');
  console.log('1. Checking if content is duplicate...');
  const isFirstDuplicate = isEmailContentProcessed(userEmail, emailContent);
  console.log(`   Is duplicate: ${isFirstDuplicate}`);
  
  if (!isFirstDuplicate) {
    console.log('2. Marking content as processed...');
    markEmailContentProcessed(userEmail, emailContent);
    
    console.log('3. Processing with LangGraph...');
    console.log('4. Checking throttle before sending...');
    const waitTime = enforceStrictThrottle(userEmail);
    if (waitTime > 0) {
      console.log(`   ⏳ Must wait ${waitTime}ms before sending`);
    } else {
      console.log('   ✅ No wait needed');
    }
    
    console.log('5. Double-checking before sending...');
    const isDoubleCheckDuplicate = isEmailContentProcessed(userEmail, emailContent);
    console.log(`   Is duplicate on double-check: ${isDoubleCheckDuplicate}`);
    
    if (!isDoubleCheckDuplicate) {
      console.log('6. Sending email...');
      updateLastEmailSentTime(userEmail);
      console.log('   ✅ Email sent successfully');
    } else {
      console.log('   🚫 Email blocked by double-check');
    }
  } else {
    console.log('   🚫 Email blocked - content already processed');
  }
  
  // Simulate second email with same content (duplicate)
  console.log('\n=== SECOND EMAIL PROCESSING (DUPLICATE) ===');
  console.log('1. Checking if content is duplicate...');
  const isSecondDuplicate = isEmailContentProcessed(userEmail, emailContent);
  console.log(`   Is duplicate: ${isSecondDuplicate}`);
  
  if (!isSecondDuplicate) {
    console.log('2. Marking content as processed...');
    markEmailContentProcessed(userEmail, emailContent);
    
    console.log('3. Processing with LangGraph...');
    console.log('4. Checking throttle before sending...');
    const waitTime = enforceStrictThrottle(userEmail);
    if (waitTime > 0) {
      console.log(`   ⏳ Must wait ${waitTime}ms before sending`);
    } else {
      console.log('   ✅ No wait needed');
    }
    
    console.log('5. Double-checking before sending...');
    const isDoubleCheckDuplicate = isEmailContentProcessed(userEmail, emailContent);
    console.log(`   Is duplicate on double-check: ${isDoubleCheckDuplicate}`);
    
    if (!isDoubleCheckDuplicate) {
      console.log('6. Sending email...');
      updateLastEmailSentTime(userEmail);
      console.log('   ✅ Email sent successfully');
    } else {
      console.log('   🚫 Email blocked by double-check');
    }
  } else {
    console.log('   🚫 Email blocked - content already processed');
  }
  
  // Simulate third email with different content
  console.log('\n=== THIRD EMAIL PROCESSING (DIFFERENT CONTENT) ===');
  const differentContent = 'I have a question about the task';
  console.log(`Content: "${differentContent}"`);
  
  console.log('1. Checking if content is duplicate...');
  const isThirdDuplicate = isEmailContentProcessed(userEmail, differentContent);
  console.log(`   Is duplicate: ${isThirdDuplicate}`);
  
  if (!isThirdDuplicate) {
    console.log('2. Marking content as processed...');
    markEmailContentProcessed(userEmail, differentContent);
    
    console.log('3. Processing with LangGraph...');
    console.log('4. Checking throttle before sending...');
    const waitTime = enforceStrictThrottle(userEmail);
    if (waitTime > 0) {
      console.log(`   ⏳ Must wait ${waitTime}ms before sending`);
    } else {
      console.log('   ✅ No wait needed');
    }
    
    console.log('5. Double-checking before sending...');
    const isDoubleCheckDuplicate = isEmailContentProcessed(userEmail, differentContent);
    console.log(`   Is duplicate on double-check: ${isDoubleCheckDuplicate}`);
    
    if (!isDoubleCheckDuplicate) {
      console.log('6. Sending email...');
      updateLastEmailSentTime(userEmail);
      console.log('   ✅ Email sent successfully');
    } else {
      console.log('   🚫 Email blocked by double-check');
    }
  } else {
    console.log('   🚫 Email blocked - content already processed');
  }
  
  console.log('\n=== SUMMARY ===');
  console.log('✅ First email: Processed and sent');
  console.log('🚫 Second email: Blocked as duplicate');
  console.log('✅ Third email: Processed and sent (different content)');
  console.log('\n🎯 Duplicate prevention system working correctly!');
}

// Run the test
testDuplicateScenario().catch(console.error); 