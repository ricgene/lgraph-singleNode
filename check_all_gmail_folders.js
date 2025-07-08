#!/usr/bin/env node
/**
 * Check All Gmail Folders
 * 
 * This script checks all Gmail folders to find where emails are actually located.
 */

const Imap = require('imap');
require('dotenv').config();

const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;

console.log('🔍 Checking All Gmail Folders');
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

// Check a specific folder
async function checkFolder(imap, folderName) {
  return new Promise((resolve, reject) => {
    imap.openBox(folderName, false, (err, box) => {
      if (err) {
        console.log(`❌ Error opening ${folderName}: ${err.message}`);
        resolve({ folder: folderName, count: 0, error: err.message });
        return;
      }
      
      console.log(`📁 ${folderName}: ${box.messages.total} messages`);
      
      if (box.messages.total === 0) {
        resolve({ folder: folderName, count: 0 });
        return;
      }
      
      // Search for recent emails (last 5)
      imap.search(['ALL'], (err, results) => {
        if (err) {
          console.error(`❌ Search error in ${folderName}:`, err);
          resolve({ folder: folderName, count: box.messages.total, error: err.message });
          return;
        }
        
        const recentEmails = results.slice(-5);
        console.log(`   📧 Checking ${recentEmails.length} recent emails...`);
        
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
            console.log(`     📧 UID: ${uid} | From: ${from} | Subject: ${subject}`);
            
            // Check if this looks like a task email from Helen
            const isHelenEmail = from.includes('helen') || subject.toLowerCase().includes('task');
            if (isHelenEmail) {
              console.log(`       🎯 DETECTED: Task email from Helen!`);
            }
          });
        });
        
        fetch.once('error', (err) => {
          console.error(`❌ Fetch error in ${folderName}:`, err);
          resolve({ folder: folderName, count: box.messages.total, error: err.message });
        });
        
        fetch.once('end', () => {
          resolve({ folder: folderName, count: box.messages.total });
        });
      });
    });
  });
}

// Main function
async function checkAllFolders() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();
    
    imap.once('ready', () => {
      console.log('✅ IMAP connection ready');
      
      // List all folders
      imap.getBoxes((err, boxes) => {
        if (err) {
          console.error('❌ Error listing folders:', err);
          imap.end();
          reject(err);
          return;
        }
        
        console.log('\n📁 Available folders:');
        const folderNames = [];
        
        function collectFolders(boxes, prefix = '') {
          for (const [name, box] of Object.entries(boxes)) {
            const fullPath = prefix ? `${prefix}/${name}` : name;
            folderNames.push(fullPath);
            console.log(`   ${fullPath}`);
            if (box.children) {
              collectFolders(box.children, fullPath);
            }
          }
        }
        
        collectFolders(boxes);
        
        console.log(`\n🔍 Checking ${folderNames.length} folders for emails...`);
        
        // Check each folder
        let checkedCount = 0;
        const results = [];
        
        const checkNextFolder = async () => {
          if (checkedCount >= folderNames.length) {
            console.log('\n✅ Finished checking all folders');
            imap.end();
            resolve(results);
            return;
          }
          
          const folderName = folderNames[checkedCount];
          console.log(`\n📋 Checking folder: ${folderName}`);
          
          try {
            const result = await checkFolder(imap, folderName);
            results.push(result);
            checkedCount++;
            checkNextFolder();
          } catch (error) {
            console.error(`❌ Error checking ${folderName}:`, error);
            results.push({ folder: folderName, count: 0, error: error.message });
            checkedCount++;
            checkNextFolder();
          }
        };
        
        checkNextFolder();
      });
    });
    
    imap.once('error', (err) => {
      console.error('❌ IMAP connection error:', err);
      reject(err);
    });
    
    imap.once('end', () => {
      console.log('🔚 IMAP connection ended');
      resolve([]);
    });
    
    imap.connect();
  });
}

// Run the check
async function main() {
  try {
    const results = await checkAllFolders();
    
    console.log('\n📊 Summary:');
    console.log('=' * 30);
    
    const foldersWithEmails = results.filter(r => r.count > 0);
    
    if (foldersWithEmails.length === 0) {
      console.log('ℹ️ No emails found in any folder');
    } else {
      console.log(`📧 Found emails in ${foldersWithEmails.length} folders:`);
      foldersWithEmails.forEach(result => {
        console.log(`   ${result.folder}: ${result.count} messages`);
      });
    }
    
    console.log('\n💡 Next steps:');
    console.log('   - If emails are in "Sent Mail", they were sent from this account');
    console.log('   - If emails are in "All Mail", check Gmail filters');
    console.log('   - If emails are in "Spam", check spam settings');
    console.log('   - If no emails found, verify the email address and sending');
    
  } catch (error) {
    console.error('❌ Check failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { checkAllFolders }; 