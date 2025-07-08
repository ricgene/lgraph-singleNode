#!/usr/bin/env node
/**
 * Email Deletion Verification Test
 * 
 * This script verifies that the email deletion functionality is working
 * correctly by checking the current state of emails and testing the process.
 */

const Imap = require('imap');
require('dotenv').config();

const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;

console.log('🔍 Email Deletion Verification Test');
console.log('=' * 50);

// IMAP connection
function createImapConnection() {
  return new Imap({
    user: GMAIL_USER,
    password: GMAIL_APP_PASSWORD,
    host: 'imap.gmail.com',
    port: 993,
    tls: true,
    tlsOptions: { rejectUnauthorized: false }
  });
}

// Check current email state
async function checkEmailState() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();
    
    imap.once('ready', () => {
      console.log('✅ IMAP connection ready');
      
      imap.openBox('INBOX', false, (err, box) => {
        if (err) {
          console.error('❌ Error opening INBOX:', err);
          imap.end();
          reject(err);
          return;
        }
        
        console.log(`📧 INBOX opened. Total messages: ${box.messages.total}`);
        
        if (box.messages.total === 0) {
          console.log('ℹ️ No emails in INBOX');
          imap.end();
          resolve();
          return;
        }
        
        // Search for recent emails
        imap.search(['ALL'], (err, results) => {
          if (err) {
            console.error('❌ Search error:', err);
            imap.end();
            reject(err);
            return;
          }
          
          const recentEmails = results.slice(-10);
          console.log(`📋 Found ${recentEmails.length} recent emails`);
          
          const fetch = imap.fetch(recentEmails, { bodies: '', struct: true });
          
          fetch.on('message', (msg, seqno) => {
            let uid = null;
            let subject = '';
            let from = '';
            let date = '';
            
            msg.on('attributes', (attrs) => {
              uid = attrs.uid;
              subject = attrs.envelope?.subject || 'No subject';
              from = attrs.envelope?.from?.[0]?.address || 'Unknown';
              date = attrs.envelope?.date || 'Unknown';
            });
            
            msg.on('body', (stream) => {
              console.log(`\n📧 Email ${seqno}:`);
              console.log(`   UID: ${uid}`);
              console.log(`   From: ${from}`);
              console.log(`   Subject: ${subject}`);
              console.log(`   Date: ${date}`);
              
              // Check if this looks like a task email from Helen
              const isHelenEmail = from.includes('helen') || subject.toLowerCase().includes('task');
              if (isHelenEmail) {
                console.log(`   🎯 Detected as potential task email from Helen`);
              }
            });
          });
          
          fetch.once('error', (err) => {
            console.error('❌ Fetch error:', err);
            imap.end();
            reject(err);
          });
          
          fetch.once('end', () => {
            console.log('\n✅ Email state check completed');
            imap.end();
            resolve();
          });
        });
      });
    });
    
    imap.once('error', (err) => {
      console.error('❌ IMAP connection error:', err);
      reject(err);
    });
    
    imap.once('end', () => {
      console.log('🔚 IMAP connection ended');
      resolve();
    });
    
    imap.connect();
  });
}

// Test the email watcher function
async function testEmailWatcher() {
  console.log('\n🧪 Testing Email Watcher Function');
  console.log('=' * 40);
  
  try {
    const response = await fetch('https://email-watcher-cs64iuly6q-uc.a.run.app', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      const result = await response.text();
      console.log('✅ Email watcher function executed successfully');
      console.log('📝 Response:', result);
    } else {
      console.error('❌ Email watcher function failed:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('❌ Error calling email watcher function:', error.message);
  }
}

// Main test function
async function main() {
  try {
    console.log('🚀 Starting email deletion verification...\n');
    
    // Step 1: Check current email state
    console.log('📋 Step 1: Checking current email state');
    await checkEmailState();
    
    // Step 2: Test email watcher function
    console.log('\n📋 Step 2: Testing email watcher function');
    await testEmailWatcher();
    
    // Step 3: Check email state again after processing
    console.log('\n📋 Step 3: Checking email state after processing');
    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
    await checkEmailState();
    
    console.log('\n✅ Email deletion verification completed!');
    console.log('\n📝 Summary:');
    console.log('   - If you see fewer emails in Step 3 than Step 1, deletion is working');
    console.log('   - If you see the same number, emails may not be getting processed');
    console.log('   - Check the email watcher logs for detailed processing information');
    
  } catch (error) {
    console.error('❌ Verification failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { checkEmailState, testEmailWatcher }; 