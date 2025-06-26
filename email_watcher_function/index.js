const Imap = require('imap');
const { simpleParser } = require('mailparser');
const { PubSub } = require('@google-cloud/pubsub');
require('dotenv').config();

const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;
const TOPIC_NAME = 'incoming-messages';

console.log('Gmail User:', GMAIL_USER);
console.log('Starting email watcher function...');

const pubsub = new PubSub();

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

// Fetch Gmail labels for a specific UID
async function getGmailLabels(imap, uid) {
  return new Promise((resolve, reject) => {
    const fetch = imap.fetch(uid, { bodies: [], struct: true, extensions: true });
    let labels = [];
    fetch.on('message', (msg) => {
      msg.on('attributes', (attrs) => {
        labels = attrs['x-gm-labels'] || [];
      });
    });
    fetch.once('error', (err) => reject(err));
    fetch.once('end', () => resolve(labels));
  });
}

// Delete email by UID (add \Deleted flag, then expunge)
async function deleteEmail(imap, uid) {
  return new Promise((resolve, reject) => {
    imap.addFlags(uid, '\\Deleted', (err) => {
      if (err) {
        console.log('⚠️ Could not mark email for deletion:', err);
        return reject(err);
      }
      console.log('✅ Marked email for deletion');
      imap.expunge((err) => {
        if (err) {
          console.log('⚠️ Could not expunge deleted emails:', err);
          return reject(err);
        }
        console.log('✅ Deleted email from INBOX');
        resolve();
      });
    });
  });
}

async function processEmail(imap, stream, info) {
  try {
    const parsed = await simpleParser(stream);
    const messageId = parsed.messageId;
    const from = parsed.from?.value?.[0]?.address;
    const subject = parsed.subject;
    const text = parsed.text || '';

    console.log(`🔍 Processing: ${subject} from "${parsed.from?.value?.[0]?.name}" <${from}>`);

    if (!subject || !subject.toLowerCase().includes('your new task')) {
      console.log(`⏭️ Skipping email with subject: ${subject}`);
      return;
    }

    // Check for "Processed" label
    if (info.uid) {
      const labels = await getGmailLabels(imap, info.uid);
      if (labels.map(l => l.toLowerCase()).includes('processed')) {
        console.log(`🚫 Already processed: ${messageId}`);
        return;
      }
    }

    console.log(`✅ MATCH FOUND! Processing email with subject: ${subject}`);
    console.log(`📧 From: ${from}`);
    console.log(`📝 Text preview: ${text.substring(0, 100)}...`);

    const message = {
      userEmail: from,
      userResponse: text,
      taskTitle: subject,
      timestamp: new Date().toISOString(),
      messageId: messageId,
      uid: info.uid
    };

    console.log('📤 Publishing to Pub/Sub:', JSON.stringify(message, null, 2));
    try {
      const messageBuffer = Buffer.from(JSON.stringify(message));
      const publishedId = await pubsub.topic(TOPIC_NAME).publish(messageBuffer);
      console.log('✅ Published message', publishedId);

      // Delete email after successful publish
      if (info.uid) {
        await deleteEmail(imap, info.uid);
      } else {
        console.log('⚠️ No UID available for deleting email');
      }
    } catch (error) {
      console.error('❌ Failed to publish to Pub/Sub:', error);
    }
  } catch (error) {
    console.error('❌ Error processing email:', error);
  }
}

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
