const Imap = require('imap');
const { simpleParser } = require('mailparser');
const { PubSub } = require('@google-cloud/pubsub');
require('dotenv').config();

// Simple config
const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;
const POLL_INTERVAL = 10000; // 10 seconds

console.log('Gmail User:', GMAIL_USER);
console.log('Starting minimal email watcher...');

// Simple tracking
const processedEmails = new Set();
const pubsub = new PubSub();
const topicName = 'incoming-messages';

// Simple IMAP connection
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

// Process a single email
async function processEmail(imap, message) {
  return new Promise((resolve, reject) => {
    const fetch = imap.fetch(message, { bodies: '' });
    
    fetch.on('message', (msg) => {
      msg.on('body', async (stream) => {
        try {
          const parsed = await simpleParser(stream);
          const messageId = parsed.messageId;
          const from = parsed.from?.text || '';
          const subject = parsed.subject || '';
          const text = parsed.text || '';
          
          console.log(`Processing: ${subject} from ${from}`);
          
          // Skip if already processed
          if (processedEmails.has(messageId)) {
            console.log(`Already processed: ${messageId}`);
            resolve();
            return;
          }
          
          // Check if this is a relevant email
          if (!subject.includes('Prizm') && !subject.includes('AI Assistant')) {
            console.log(`Skipping non-Prizm email: ${subject}`);
            resolve();
            return;
          }
          
          // Extract user email
          const userEmailMatch = from.match(/<(.+?)>/);
          const userEmail = userEmailMatch ? userEmailMatch[1] : from;
          
          if (!userEmail.includes('@')) {
            console.log(`Invalid email: ${userEmail}`);
            resolve();
            return;
          }
          
          console.log(`Processing reply from: ${userEmail}`);
          processedEmails.add(messageId);
          
          // Publish to Pub/Sub
          const messageData = {
            userEmail: userEmail,
            message: text,
            taskTitle: 'Prizm Task Question',
            timestamp: new Date().toISOString()
          };
          
          const messageBuffer = Buffer.from(JSON.stringify(messageData));
          const messageId_pubsub = await pubsub.topic(topicName).publish(messageBuffer);
          console.log(`✅ Published message ${messageId_pubsub}`);
          
          resolve();
          
        } catch (error) {
          console.error('Error processing email:', error);
          reject(error);
        }
      });
    });
    
    fetch.on('error', reject);
    fetch.on('end', resolve);
  });
}

// Check emails
async function checkEmails() {
  const imap = createImapConnection();
  
  return new Promise((resolve, reject) => {
    imap.once('ready', () => {
      imap.openBox('INBOX', false, (err) => {
        if (err) {
          reject(err);
          return;
        }
        
        imap.search(['UNSEEN'], (err, results) => {
          if (err) {
            reject(err);
            return;
          }
          
          if (results.length === 0) {
            console.log('No new emails');
            imap.end();
            resolve();
            return;
          }
          
          console.log(`Found ${results.length} new emails`);
          
          // Process sequentially
          let index = 0;
          const processNext = async () => {
            if (index >= results.length) {
              imap.end();
              resolve();
              return;
            }
            
            try {
              await processEmail(imap, results[index]);
              index++;
              processNext();
            } catch (error) {
              console.error(`Error processing email ${index}:`, error);
              index++;
              processNext();
            }
          };
          
          processNext();
        });
      });
    });
    
    imap.once('error', reject);
    imap.once('end', () => console.log('IMAP connection ended'));
    imap.connect();
  });
}

// Main loop
async function main() {
  console.log('Email watcher running. Press Ctrl+C to stop.');
  
  while (true) {
    try {
      await checkEmails();
    } catch (error) {
      console.error('Error in polling cycle:', error);
    }
    
    await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
  }
}

process.on('SIGINT', () => {
  console.log('\nShutting down...');
  process.exit(0);
});

main().catch(console.error); 