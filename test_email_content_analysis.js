#!/usr/bin/env node
/**
 * Email Content Analysis
 * 
 * This script analyzes email content to see if it matches task creation criteria.
 */

const Imap = require('imap');
const { simpleParser } = require('mailparser');
require('dotenv').config();

const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;

console.log('🔍 Email Content Analysis');
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

// Check if email is a task creation email (same logic as email watcher)
function checkIfTaskCreationEmail(parsed) {
  const subject = parsed.subject?.toLowerCase() || '';
  const text = parsed.text?.toLowerCase() || '';
  const html = parsed.html?.toLowerCase() || '';
  
  const taskKeywords = [
    'new task',
    'task creation',
    'customer name',
    'task budget',
    'due date',
    'full address',
    'category',
    'vendors',
    'your new task'
  ];
  
  const emailContent = `${subject} ${text} ${html}`;
  
  const matches = taskKeywords.filter(keyword => emailContent.includes(keyword));
  
  return {
    isTaskEmail: taskKeywords.some(keyword => emailContent.includes(keyword)) ||
                emailContent.includes('customer name:') ||
                emailContent.includes('task:') ||
                emailContent.includes('budget:') ||
                emailContent.includes('address:'),
    matches: matches,
    content: emailContent
  };
}

// Analyze emails in a folder
async function analyzeFolder(imap, folderName) {
  return new Promise((resolve, reject) => {
    imap.openBox(folderName, false, (err, box) => {
      if (err) {
        console.log(`❌ Error opening ${folderName}: ${err.message}`);
        resolve([]);
        return;
      }
      
      console.log(`📁 ${folderName}: ${box.messages.total} messages`);
      
      if (box.messages.total === 0) {
        resolve([]);
        return;
      }
      
      // Get recent emails (last 10)
      imap.search(['ALL'], (err, results) => {
        if (err) {
          console.error(`❌ Search error in ${folderName}:`, err);
          resolve([]);
          return;
        }
        
        const recentEmails = results.slice(-10);
        console.log(`   📧 Analyzing ${recentEmails.length} recent emails...`);
        
        const fetch = imap.fetch(recentEmails, { bodies: '', struct: true });
        const emailAnalysis = [];
        
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
          
          msg.on('body', async (stream) => {
            try {
              const parsed = await simpleParser(stream);
              const analysis = checkIfTaskCreationEmail(parsed);
              
              const emailInfo = {
                uid,
                from,
                subject,
                date,
                isTaskEmail: analysis.isTaskEmail,
                matches: analysis.matches,
                content: analysis.content.substring(0, 200) + '...',
                messageId: parsed.messageId
              };
              
              emailAnalysis.push(emailInfo);
              
              console.log(`\n📧 Email ${seqno}:`);
              console.log(`   UID: ${uid}`);
              console.log(`   From: ${from}`);
              console.log(`   Subject: ${subject}`);
              console.log(`   Is Task Email: ${analysis.isTaskEmail ? '✅ YES' : '❌ NO'}`);
              if (analysis.matches.length > 0) {
                console.log(`   Matches: ${analysis.matches.join(', ')}`);
              }
              console.log(`   Content Preview: ${analysis.content.substring(0, 100)}...`);
              
              // Check if this looks like a task email from Helen
              const isHelenEmail = from.includes('helen') || subject.toLowerCase().includes('task');
              if (isHelenEmail) {
                console.log(`   🎯 DETECTED: Potential task email from Helen!`);
                console.log(`   📋 Full Content: ${analysis.content}`);
              }
              
            } catch (error) {
              console.error(`❌ Error parsing email ${seqno}:`, error);
            }
          });
        });
        
        fetch.once('error', (err) => {
          console.error(`❌ Fetch error in ${folderName}:`, err);
          resolve(emailAnalysis);
        });
        
        fetch.once('end', () => {
          resolve(emailAnalysis);
        });
      });
    });
  });
}

// Main function
async function analyzeAllEmails() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();
    
    imap.once('ready', async () => {
      console.log('✅ IMAP connection ready');
      
      try {
        // Check key folders
        const folders = ['INBOX', '[Gmail]/All Mail', '[Gmail]/Sent Mail'];
        const allAnalysis = [];
        
        for (const folder of folders) {
          console.log(`\n📋 Analyzing folder: ${folder}`);
          const analysis = await analyzeFolder(imap, folder);
          allAnalysis.push(...analysis);
        }
        
        console.log('\n📊 Analysis Summary:');
        console.log('=' * 40);
        
        const taskEmails = allAnalysis.filter(email => email.isTaskEmail);
        const helenEmails = allAnalysis.filter(email => 
          email.from.includes('helen') || email.subject.toLowerCase().includes('task')
        );
        
        console.log(`📧 Total emails analyzed: ${allAnalysis.length}`);
        console.log(`🎯 Task emails detected: ${taskEmails.length}`);
        console.log(`👤 Helen/task-related emails: ${helenEmails.length}`);
        
        if (helenEmails.length > 0) {
          console.log('\n🎯 Helen/Task Emails Found:');
          helenEmails.forEach((email, index) => {
            console.log(`\n   ${index + 1}. From: ${email.from}`);
            console.log(`      Subject: ${email.subject}`);
            console.log(`      Is Task Email: ${email.isTaskEmail ? '✅ YES' : '❌ NO'}`);
            if (email.matches.length > 0) {
              console.log(`      Matches: ${email.matches.join(', ')}`);
            }
            console.log(`      Content: ${email.content}`);
          });
        }
        
        if (taskEmails.length > 0) {
          console.log('\n📋 Task Emails Found:');
          taskEmails.forEach((email, index) => {
            console.log(`\n   ${index + 1}. From: ${email.from}`);
            console.log(`      Subject: ${email.subject}`);
            console.log(`      Matches: ${email.matches.join(', ')}`);
          });
        }
        
        imap.end();
        resolve(allAnalysis);
        
      } catch (error) {
        console.error('❌ Analysis error:', error);
        imap.end();
        reject(error);
      }
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

// Run the analysis
async function main() {
  try {
    const analysis = await analyzeAllEmails();
    
    console.log('\n💡 Recommendations:');
    console.log('=' * 30);
    
    if (analysis.length === 0) {
      console.log('   - No emails found in any folder');
      console.log('   - Verify emails are being sent to the correct address');
    } else {
      const helenEmails = analysis.filter(email => 
        email.from.includes('helen') || email.subject.toLowerCase().includes('task')
      );
      
      if (helenEmails.length === 0) {
        console.log('   - No emails from Helen found');
        console.log('   - Verify Helen is sending to the correct email address');
        console.log('   - Check if emails are being filtered by Gmail');
      } else {
        const taskEmails = helenEmails.filter(email => email.isTaskEmail);
        if (taskEmails.length === 0) {
          console.log('   - Helen emails found but not detected as task emails');
          console.log('   - Check email content for required keywords');
          console.log('   - Update task detection logic if needed');
        } else {
          console.log('   - Task emails found but not being processed');
          console.log('   - Check email watcher logs for processing errors');
        }
      }
    }
    
  } catch (error) {
    console.error('❌ Analysis failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { analyzeAllEmails }; 