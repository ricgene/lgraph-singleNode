#!/usr/bin/env node

/**
 * Get Firebase ID Token from command line
 * Usage: node get_firebase_token.js <email> <password>
 */

const { initializeApp } = require('firebase/app');
const { getAuth, signInWithEmailAndPassword } = require('firebase/auth');

// Firebase config (from your .env)
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

async function getFirebaseToken(email, password) {
  try {
    console.log(`🔐 Signing in with email: ${email}`);
    
    // Sign in with email and password
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    
    console.log(`✅ Successfully signed in as: ${user.email}`);
    
    // Get the ID token
    const idToken = await user.getIdToken();
    
    console.log('\n🎫 Firebase ID Token:');
    console.log('=' * 50);
    console.log(idToken);
    console.log('=' * 50);
    
    console.log('\n📋 To use this token in your requests:');
    console.log(`curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email \\`);
    console.log(`  -H "Content-Type: application/json" \\`);
    console.log(`  -H "Authorization: Bearer ${idToken.substring(0, 20)}..." \\`);
    console.log(`  -d '{"userEmail": "${email}", "userResponse": "Test message", "taskTitle": "Test Task"}'`);
    
    return idToken;
    
  } catch (error) {
    console.error('❌ Error getting Firebase token:', error.message);
    
    if (error.code === 'auth/user-not-found') {
      console.log('\n💡 You may need to create a user account first.');
      console.log('   You can do this in the Firebase Console or using Firebase Admin SDK.');
    } else if (error.code === 'auth/wrong-password') {
      console.log('\n💡 Check your password.');
    }
    
    process.exit(1);
  }
}

// Get command line arguments
const email = process.argv[2];
const password = process.argv[3];

if (!email || !password) {
  console.log('Usage: node get_firebase_token.js <email> <password>');
  console.log('');
  console.log('Example:');
  console.log('  node get_firebase_token.js test@example.com mypassword123');
  console.log('');
  console.log('Note: You need to have a user account created in Firebase Auth first.');
  process.exit(1);
}

// Get the token
getFirebaseToken(email, password); 