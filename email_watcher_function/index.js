const Imap = require('imap');
const { simpleParser } = require('mailparser');
const { PubSub } = require('@google-cloud/pubsub');
require('dotenv').config();

// Simple config
const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;
const TOPIC_NAME = 'incoming-messages';

console.log('Gmail User:', GMAIL_USER);
console.log('Starting email watcher function...');

// Simple tracking
const processedEmails = new Set();
const pubsub = new PubSub();

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
async function processEmail(imap, stream, info) {
  try {
    const parsed = await simpleParser(stream);
    const messageId = parsed.messageId;
    const from = parsed.from?.value?.[0]?.address;
    const subject = parsed.subject;
    const text = parsed.text || '';

    console.log(`Processing: ${subject} from "${parsed.from?.value?.[0]?.name}" <${from}>`);

    // Skip if already processed
    if (processedEmails.has(messageId)) {
      console.log(`Already processed: ${messageId}`);
      return;
    }

    // Skip if not from expected user
    if (!from || !from.includes('richard.genet@gmail.com')) {
      console.log(`Skipping email from: ${from}`);
      return;
    }

    // Extract user response (simple approach)
    const userResponse = text.trim().split('\n')[0];
    console.log(`Processing reply from: ${from}`);
    console.log(`User response: ${userResponse}`);

    // Publish to Pub/Sub
    const messageData = {
      userEmail: from,
      userResponse: userResponse,
      taskTitle: 'Prizm Task Question',
      timestamp: new Date().toISOString(),
      messageId: messageId
    };

    const messageBuffer = Buffer.from(JSON.stringify(messageData));
    const messageId_pubsub = await pubsub.topic(TOPIC_NAME).publish(messageBuffer);
    console.log(`✅ Published message ${messageId_pubsub}`);

    // Mark as processed
    processedEmails.add(messageId);

  } catch (error) {
    console.error('Error processing email:', error);
  }
}

// Main function to check emails
async function checkEmails() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();

    imap.once('ready', () => {
      console.log('IMAP connection ready');
      imap.openBox('INBOX', false, (err, box) => {
        if (err) {
          console.error('Error opening inbox:', err);
          imap.end();
          reject(err);
          return;
        }

        // Search for unread emails
        imap.search(['UNSEEN'], (err, results) => {
          if (err) {
            console.error('Search error:', err);
            imap.end();
            reject(err);
            return;
          }

          if (results.length === 0) {
            console.log('No new emails found');
            imap.end();
            resolve();
            return;
          }

          console.log(`Found ${results.length} new emails`);
          
          const fetch = imap.fetch(results, { bodies: '' });
          
          fetch.on('message', (msg, seqno) => {
            msg.on('body', (stream, info) => {
              processEmail(imap, stream, info);
            });
          });

          fetch.once('error', (err) => {
            console.error('Fetch error:', err);
            imap.end();
            reject(err);
          });

          fetch.once('end', () => {
            console.log('IMAP connection ended');
            imap.end();
            resolve();
          });
        });
      });
    });

    imap.once('error', (err) => {
      console.error('IMAP connection error:', err);
      reject(err);
    });

    imap.once('end', () => {
      console.log('IMAP connection ended');
      resolve();
    });

    imap.connect();
  });
}

// Cloud Function entry point
exports.emailWatcher = async (req, res) => {
  try {
    console.log('Email watcher function triggered');
    await checkEmails();
    res.status(200).send('Email check completed successfully');
  } catch (error) {
    console.error('Function error:', error);
    res.status(500).send(`Error: ${error.message}`);
  }
}; 