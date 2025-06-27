const Imap = require('imap');
const { simpleParser } = require('mailparser');
const { PubSub } = require('@google-cloud/pubsub');
const { Firestore } = require('@google-cloud/firestore');
require('dotenv').config();

const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;
const TOPIC_NAME = 'incoming-messages';

const firestore = new Firestore();
const COLLECTION = 'processedEmails';
const pubsub = new PubSub();

console.log('Gmail User:', GMAIL_USER);
console.log('Starting email watcher function...');

// Firestore helpers with enhanced logging
async function isProcessed(messageId) {
  if (!messageId) return false;
  try {
    const doc = await firestore.collection(COLLECTION).doc(messageId).get();
    if (doc.exists) {
      console.log(`ℹ️ Message-ID ${messageId} found in Firestore (already processed)`);
      return true;
    }
    console.log(`ℹ️ Message-ID ${messageId} not found in Firestore (not processed)`);
    return false;
  } catch (err) {
    console.error(`❌ Firestore error checking processed status for ${messageId}: ${err.message}`);
    // Fail safe: treat as not processed to avoid missing emails
    return false;
  }
}

async function markProcessed(messageId, meta = {}) {
  if (!messageId) return;
  try {
    await firestore.collection(COLLECTION).doc(messageId).set({
      processedAt: new Date().toISOString(),
      ...meta
    });
    console.log(`✅ Marked as processed in Firestore: ${messageId}`);
  } catch (err) {
    console.error(`❌ Firestore error marking processed for ${messageId}: ${err.message}`);
  }
}

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

// Main email processing
async function processEmail(imap, stream, info) {
  try {
    const parsed = await simpleParser(stream);
    const messageId = parsed.messageId;
    const from = parsed.from?.value?.[0]?.address;
    const subject = parsed.subject;
    const text = parsed.text || '';

    if (!messageId) {
      console.log('No Message-ID found, skipping.');
      return;
    }

    // Firestore deduplication with logging
    if (await isProcessed(messageId)) {
      console.log(`🚫 Already processed: ${messageId}`);
      return;
    }

    if (!subject || !subject.toLowerCase().includes('your new task')) {
      console.log(`⏭️ Skipping email with subject: ${subject}`);
      return;
    }

    console.log(`✅ MATCH FOUND! Processing email with subject: ${subject}`);
    console.log(`📧 From: ${from}`);
    console.log(`📝 Text preview: ${text.substring(0, 100)}...`);

    const message = {
      userEmail: from,
      userResponse: text,
      taskTitle: subject,
      timestamp: new Date().toISOString(),
      messageId: messageId
    };

    // Publish to Pub/Sub
    try {
      const messageBuffer = Buffer.from(JSON.stringify(message));
      const publishedId = await pubsub.topic(TOPIC_NAME).publish(messageBuffer);
      console.log('✅ Published message', publishedId);

      // Mark as processed in Firestore with logging
      await markProcessed(messageId, { from, subject });
    } catch (error) {
      console.error('❌ Failed to publish to Pub/Sub:', error);
    }
  } catch (error) {
    console.error('❌ Error processing email:', error);
  }
}

// List folders for debugging
function listFolders(imap) {
  return new Promise((resolve, reject) => {
    imap.getBoxes((err, boxes) => {
      if (err) {
        console.error('Error listing folders:', err);
        reject(err);
        return;
      }
      console.log('📁 Available folders:');
      function printBoxes(boxes, prefix = '') {
        for (const [name, box] of Object.entries(boxes)) {
          console.log(`${prefix}${name}: ${box.path}`);
          if (box.children) {
            printBoxes(box.children, prefix + '  ');
          }
        }
      }
      printBoxes(boxes);
      resolve(boxes);
    });
  });
}

// Main check function
async function checkEmails() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();
    let pendingOperations = 0;

    imap.once('ready', async () => {
      console.log('IMAP connection ready');
      try {
        await listFolders(imap);
        imap.openBox('INBOX', false, (err, box) => {
          if (err) {
            console.error('Error opening INBOX:', err);
            imap.end();
            resolve();
            return;
          }
          console.log('Checking folder: INBOX');
          imap.search(['ALL'], (err, results) => {
            if (err) {
              console.error('Search error in INBOX:', err);
              imap.end();
              resolve();
              return;
            }
            if (results.length === 0) {
              console.log('No emails found in INBOX');
              imap.end();
              resolve();
              return;
            }
            console.log(`Found ${results.length} emails in INBOX`);
            const recentEmails = results.slice(-10);
            console.log(`Processing ${recentEmails.length} most recent emails`);
            const fetch = imap.fetch(recentEmails, { bodies: '', struct: true, extensions: true });
            fetch.on('message', (msg, seqno) => {
              let uid = null;
              msg.on('attributes', (attrs) => {
                uid = attrs.uid;
              });
              msg.on('body', (stream, info) => {
                pendingOperations++;
                processEmail(imap, stream, { uid: uid, seqno: seqno }).finally(() => {
                  pendingOperations--;
                  if (pendingOperations === 0) {
                    setTimeout(() => {
                      console.log('Finished processing INBOX');
                      imap.end();
                      resolve();
                    }, 2000);
                  }
                });
              });
            });
            fetch.once('error', (err) => {
              console.error('Fetch error in INBOX:', err);
              imap.end();
              resolve();
            });
            fetch.once('end', () => {
              if (pendingOperations === 0) {
                setTimeout(() => {
                  console.log('Finished processing INBOX');
                  imap.end();
                  resolve();
                }, 2000);
              }
            });
          });
        });
      } catch (error) {
        console.error('Error in checkEmails:', error);
        imap.end();
        resolve();
      }
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

// Exported function for serverless/cloud function use
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
