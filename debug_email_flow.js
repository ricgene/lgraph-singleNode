#!/usr/bin/env node
/**
 * Debug Email Flow
 * 
 * This script helps debug why emails aren't being processed and task records aren't being created.
 */

const Imap = require('imap');
const { simpleParser } = require('mailparser');
require('dotenv').config();

const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;

console.log('🔍 Debug Email Flow');
console.log('=' * 50);
console.log(`📧 Monitoring email address: ${GMAIL_USER}`);

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

// Check recent emails in all folders
async function checkRecentEmails() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();
    
    imap.once('ready', () => {
      console.log('✅ IMAP connection ready');
      
      const folders = ['INBOX', '[Gmail]/All Mail', '[Gmail]/Sent Mail'];
      let checkedFolders = 0;
      const allEmails = [];
      
      folders.forEach(folderName => {
        imap.openBox(folderName, false, (err, box) => {
          if (err) {
            console.log(`❌ Error opening ${folderName}: ${err.message}`);
            checkedFolders++;
            if (checkedFolders === folders.length) {
              imap.end();
              resolve(allEmails);
            }
            return;
          }
          
          console.log(`\n📁 ${folderName}: ${box.messages.total} messages`);
          
          if (box.messages.total === 0) {
            checkedFolders++;
            if (checkedFolders === folders.length) {
              imap.end();
              resolve(allEmails);
            }
            return;
          }
          
          // Get the 5 most recent emails
          imap.search(['ALL'], (err, results) => {
            if (err) {
              console.error(`❌ Search error in ${folderName}:`, err);
              checkedFolders++;
              if (checkedFolders === folders.length) {
                imap.end();
                resolve(allEmails);
              }
              return;
            }
            
            const recentEmails = results.slice(-5);
            console.log(`   📧 Checking ${recentEmails.length} recent emails...`);
            
            const fetch = imap.fetch(recentEmails, { bodies: '', struct: true });
            
            fetch.on('message', (msg, seqno) => {
              let uid = null;
              let subject = '';
              let from = '';
              let to = '';
              let date = '';
              
              msg.on('attributes', (attrs) => {
                uid = attrs.uid;
                subject = attrs.envelope?.subject || 'No subject';
                from = attrs.envelope?.from?.[0]?.address || 'Unknown';
                to = attrs.envelope?.to?.[0]?.address || 'Unknown';
                date = attrs.envelope?.date || 'Unknown';
              });
              
              msg.on('body', async (stream) => {
                try {
                  const parsed = await simpleParser(stream);
                  
                  const emailInfo = {
                    folder: folderName,
                    uid,
                    from,
                    to,
                    subject,
                    date,
                    messageId: parsed.messageId,
                    text: parsed.text?.substring(0, 200) || '',
                    isFromHelen: from.includes('helen'),
                    isToCorrectAddress: to === GMAIL_USER,
                    isFromSameAccount: from === GMAIL_USER
                  };
                  
                  allEmails.push(emailInfo);
                  
                  console.log(`\n📧 Email ${seqno} in ${folderName}:`);
                  console.log(`   UID: ${uid}`);
                  console.log(`   From: ${from}`);
                  console.log(`   To: ${to}`);
                  console.log(`   Subject: ${subject}`);
                  console.log(`   Date: ${date}`);
                  console.log(`   Is from Helen: ${emailInfo.isFromHelen ? '✅ YES' : '❌ NO'}`);
                  console.log(`   Is to correct address: ${emailInfo.isToCorrectAddress ? '✅ YES' : '❌ NO'}`);
                  console.log(`   Is from same account: ${emailInfo.isFromSameAccount ? '✅ YES' : '❌ NO'}`);
                  
                  if (emailInfo.isFromHelen) {
                    console.log(`   🎯 DETECTED: Email from Helen!`);
                    console.log(`   📝 Content preview: ${emailInfo.text}`);
                  }
                  
                } catch (error) {
                  console.error(`❌ Error parsing email ${seqno}:`, error);
                }
              });
            });
            
            fetch.once('error', (err) => {
              console.error(`❌ Fetch error in ${folderName}:`, err);
            });
            
            fetch.once('end', () => {
              checkedFolders++;
              if (checkedFolders === folders.length) {
                imap.end();
                resolve(allEmails);
              }
            });
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
      resolve(allEmails);
    });
    
    imap.connect();
  });
}

// Main function
async function main() {
  try {
    console.log('🚀 Starting email flow debug...\n');
    
    const emails = await checkRecentEmails();
    
    console.log('\n📊 Analysis Summary:');
    console.log('=' * 40);
    
    const helenEmails = emails.filter(email => email.isFromHelen);
    const emailsToCorrectAddress = emails.filter(email => email.isToCorrectAddress);
    const emailsFromSameAccount = emails.filter(email => email.isFromSameAccount);
    
    console.log(`📧 Total emails found: ${emails.length}`);
    console.log(`👤 Emails from Helen: ${helenEmails.length}`);
    console.log(`📮 Emails to ${GMAIL_USER}: ${emailsToCorrectAddress.length}`);
    console.log(`📤 Emails from same account: ${emailsFromSameAccount.length}`);
    
    if (helenEmails.length === 0) {
      console.log('\n❌ No emails from Helen found!');
      console.log('\n💡 Possible issues:');
      console.log('   1. Helen is not sending emails to this address');
      console.log('   2. Helen is using a different email address');
      console.log('   3. Emails are being sent to a different address');
      console.log('   4. Emails are being filtered by Gmail');
    } else {
      console.log('\n✅ Emails from Helen found!');
      helenEmails.forEach((email, index) => {
        console.log(`\n   ${index + 1}. Folder: ${email.folder}`);
        console.log(`      From: ${email.from}`);
        console.log(`      To: ${email.to}`);
        console.log(`      Subject: ${email.subject}`);
        console.log(`      Is to correct address: ${email.isToCorrectAddress ? '✅ YES' : '❌ NO'}`);
      });
    }
    
    if (emailsToCorrectAddress.length === 0) {
      console.log('\n❌ No emails sent to the correct address!');
      console.log(`   Expected address: ${GMAIL_USER}`);
      console.log('\n💡 Check:');
      console.log('   1. What address is Helen actually sending to?');
      console.log('   2. Are there any typos in the email address?');
      console.log('   3. Is Helen using the right email address?');
    }
    
    if (emailsFromSameAccount.length > 0) {
      console.log('\n📤 Found emails sent from this account:');
      emailsFromSameAccount.forEach((email, index) => {
        console.log(`   ${index + 1}. To: ${email.to}`);
        console.log(`      Subject: ${email.subject}`);
        console.log(`      Folder: ${email.folder}`);
      });
    }
    
    console.log('\n🔍 Next Steps:');
    console.log('=' * 20);
    console.log('1. Verify Helen is sending to the correct email address');
    console.log('2. Check Gmail filters and settings');
    console.log('3. Test sending an email to this address');
    console.log('4. Check if emails are being filtered to spam or other folders');
    
  } catch (error) {
    console.error('❌ Debug failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { checkRecentEmails }; 