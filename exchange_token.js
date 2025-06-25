#!/usr/bin/env node

/**
 * Exchange custom token for ID token
 * Usage: node exchange_token.js <custom_token>
 */

const { initializeApp } = require('firebase/app');
const { getAuth, signInWithCustomToken } = require('firebase/auth');

// Firebase config
const firebaseConfig = {
  apiKey: "AIzaSyCyO4TZBIILJeJcVXBaB1rEWPWBbhb2WA8",
  authDomain: "prizmpoc.firebaseapp.com",
  projectId: "prizmpoc",
  storageBucket: "prizmpoc.appspot.com",
  messagingSenderId: "324482404818",
  appId: "1:324482404818:web:065e631480a579c182b80b"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

async function exchangeCustomToken(customToken) {
  try {
    console.log('🔄 Exchanging custom token for ID token...');
    
    // Sign in with custom token
    const userCredential = await signInWithCustomToken(auth, customToken);
    const user = userCredential.user;
    
    console.log(`✅ Successfully signed in as: ${user.email || user.uid}`);
    
    // Get the ID token
    const idToken = await user.getIdToken();
    
    console.log('\n🎫 Firebase ID Token (ready for cloud function):');
    console.log('=' * 60);
    console.log(idToken);
    console.log('=' * 60);
    
    console.log('\n📋 Test your cloud function:');
    console.log(`curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email \\`);
    console.log(`  -H "Content-Type: application/json" \\`);
    console.log(`  -H "Authorization: Bearer ${idToken.substring(0, 20)}..." \\`);
    console.log(`  -d '{"userEmail": "test@prizmpoc.com", "userResponse": "Test message with Firebase Auth", "taskTitle": "Test Task"}'`);
    
    return idToken;
    
  } catch (error) {
    console.error('❌ Error exchanging token:', error.message);
    process.exit(1);
  }
}

// Get custom token from command line
const customToken = process.argv[2];

if (!customToken) {
  console.log('Usage: node exchange_token.js <custom_token>');
  console.log('');
  console.log('Example:');
  console.log('  node exchange_token.js eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...');
  process.exit(1);
}

// Exchange the token
exchangeCustomToken(customToken); 