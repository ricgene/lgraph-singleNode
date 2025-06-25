#!/usr/bin/env node

/**
 * Get Firebase token using service account credentials
 * This creates a custom token for testing purposes
 */

const admin = require('firebase-admin');
const path = require('path');

// Path to your service account key file
const serviceAccountPath = '/home/rgenet/fbserviceAccountKey-admin.json';

// Initialize Firebase Admin SDK with service account
if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccountPath),
    projectId: 'prizmpoc'
  });
}

async function getServiceAccountToken() {
  try {
    console.log('🔐 Using service account credentials...');
    
    // Create a custom token for a test user
    const testUserId = 'test-service-account-user';
    const customToken = await admin.auth().createCustomToken(testUserId, {
      email: 'test@prizmpoc.com',
      role: 'test-user'
    });
    
    console.log('✅ Custom token created successfully');
    console.log('\n🎫 Custom Token:');
    console.log('=' * 50);
    console.log(customToken);
    console.log('=' * 50);
    
    console.log('\n📋 To use this token in your requests:');
    console.log(`curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email \\`);
    console.log(`  -H "Content-Type: application/json" \\`);
    console.log(`  -H "Authorization: Bearer ${customToken.substring(0, 20)}..." \\`);
    console.log(`  -d '{"userEmail": "test@prizmpoc.com", "userResponse": "Test message", "taskTitle": "Test Task"}'`);
    
    return customToken;
    
  } catch (error) {
    console.error('❌ Error creating custom token:', error.message);
    process.exit(1);
  }
}

// Alternative: Create a real user and get ID token
async function createUserAndGetToken() {
  try {
    console.log('👤 Creating test user with service account...');
    
    const email = 'test@prizmpoc.com';
    const password = 'testpassword123';
    
    // Create user
    const userRecord = await admin.auth().createUser({
      email: email,
      password: password,
      displayName: 'Service Account Test User',
      emailVerified: true
    });
    
    console.log(`✅ Created user: ${userRecord.uid}`);
    
    // Generate a custom token for this user
    const customToken = await admin.auth().createCustomToken(userRecord.uid);
    
    console.log('\n🎫 Custom Token for created user:');
    console.log('=' * 50);
    console.log(customToken);
    console.log('=' * 50);
    
    console.log('\n📋 To use this token:');
    console.log(`curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email \\`);
    console.log(`  -H "Content-Type: application/json" \\`);
    console.log(`  -H "Authorization: Bearer ${customToken.substring(0, 20)}..." \\`);
    console.log(`  -d '{"userEmail": "${email}", "userResponse": "Test message", "taskTitle": "Test Task"}'`);
    
    return { userRecord, customToken };
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    
    if (error.code === 'auth/email-already-exists') {
      console.log('💡 User already exists, creating custom token...');
      return await getServiceAccountToken();
    }
    
    process.exit(1);
  }
}

// Run the function
console.log('🚀 Getting Firebase token using service account...\n');

// Try to create user first, fallback to simple custom token
createUserAndGetToken().catch(error => {
  console.error('❌ Error:', error.message);
  process.exit(1);
}); 