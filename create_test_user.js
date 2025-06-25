#!/usr/bin/env node

/**
 * Create a test user account in Firebase Auth
 * Usage: node create_test_user.js <email> <password>
 */

const admin = require('firebase-admin');

// Initialize Firebase Admin SDK
if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.applicationDefault(),
    projectId: 'prizmpoc'
  });
}

async function createTestUser(email, password) {
  try {
    console.log(`👤 Creating test user: ${email}`);
    
    // Create the user
    const userRecord = await admin.auth().createUser({
      email: email,
      password: password,
      displayName: 'Test User',
      emailVerified: true
    });
    
    console.log(`✅ Successfully created user: ${userRecord.uid}`);
    console.log(`📧 Email: ${userRecord.email}`);
    console.log(`📅 Created: ${userRecord.metadata.creationTime}`);
    
    console.log('\n🎯 Now you can get a token with:');
    console.log(`node get_firebase_token.js ${email} ${password}`);
    
    return userRecord;
    
  } catch (error) {
    console.error('❌ Error creating user:', error.message);
    
    if (error.code === 'auth/email-already-exists') {
      console.log('\n💡 User already exists. You can try to get a token directly:');
      console.log(`node get_firebase_token.js ${email} ${password}`);
    }
    
    process.exit(1);
  }
}

// Get command line arguments
const email = process.argv[2];
const password = process.argv[3];

if (!email || !password) {
  console.log('Usage: node create_test_user.js <email> <password>');
  console.log('');
  console.log('Example:');
  console.log('  node create_test_user.js test@example.com mypassword123');
  process.exit(1);
}

// Create the user
createTestUser(email, password); 