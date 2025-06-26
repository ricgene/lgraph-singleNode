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

// Global variables
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

    console.log(`🔍 Processing: ${subject} from "${parsed.from?.value?.[0]?.name}" <${from}>`);

    // Skip if not from expected user
    // We're monitoring foilboi808@gmail.com for incoming emails, so we don't filter by sender
    // Just check if the subject matches our pattern
    if (!subject || !subject.toLowerCase().includes('your new task')) {
      console.log(`⏭️ Skipping email with subject: ${subject}`);
      return;
    }

    console.log(`✅ MATCH FOUND! Processing email with subject: ${subject}`);
    console.log(`📧 From: ${from}`);
    console.log(`📝 Text preview: ${text.substring(0, 100)}...`);

    // Publish to Pub/Sub
    const message = {
      userEmail: from,
      userResponse: text,
      taskTitle: 'Prizm Task Question',
      timestamp: new Date().toISOString(),
      messageId: messageId,
      emailUid: info?.uid
    };

    console.log(`📤 Publishing to Pub/Sub: ${JSON.stringify(message, null, 2)}`);

    try {
      const messageBuffer = Buffer.from(JSON.stringify(message));
      const pubsubMessageId = await pubsub.topic(TOPIC_NAME).publish(messageBuffer);
      console.log(`✅ Published message ${pubsubMessageId}`);
      
      // Mark email as processed by moving it to the processed-tasks folder
      if (info && info.uid) {
        console.log(`📁 Attempting to move email with UID ${info.uid} to processed-tasks folder`);
        
        // First, ensure the processed-tasks folder exists
        imap.createBox('processed-tasks', (createErr) => {
          if (createErr && createErr.code !== 'ALREADYEXISTS') {
            console.error('❌ Failed to create processed-tasks folder:', createErr);
            return;
          }
          
          // Now move the email to the processed-tasks folder
          imap.move(info.uid, 'processed-tasks', (moveErr) => {
            if (moveErr) {
              console.error('❌ Failed to move email to processed-tasks:', moveErr);
            } else {
              console.log('✅ Moved email to processed-tasks folder');
            }
          });
        });
      } else {
        console.log('⚠️ No UID available for email move operation');
        console.log('📋 Info object:', JSON.stringify(info, null, 2));
      }
      
    } catch (error) {
      console.error('❌ Failed to publish to Pub/Sub:', error);
    }

  } catch (error) {
    console.error('❌ Error processing email:', error);
  }
}

// List available folders
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

// Main function to check emails
async function checkEmails() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();
    let pendingOperations = 0;

    imap.once('ready', async () => {
      console.log('IMAP connection ready');
      try {
        // List available folders (optional, for debugging)
        await listFolders(imap);
        // Only check INBOX
        imap.openBox('INBOX', false, (err, box) => {
          if (err) {
            console.error('Error opening INBOX:', err);
            imap.end();
            resolve();
            return;
          }
          console.log('Checking folder: INBOX');
          // Use ALL instead of UNSEEN to avoid IMAP protocol errors
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
            
            // Only process the most recent 10 emails to avoid overwhelming
            const recentEmails = results.slice(-10);
            console.log(`Processing ${recentEmails.length} most recent emails`);
            
            const fetch = imap.fetch(recentEmails, { bodies: '', struct: true });
            fetch.on('message', (msg, seqno) => {
              console.log(`📧 Processing message #${seqno}, attributes:`, msg.attributes);
              console.log(`📧 Message UID:`, msg.attributes?.uid);
              pendingOperations++;
              msg.on('body', (stream, info) => {
                // Skip emails that are already in processed-tasks folder
                // We can't easily check this here, so we'll let the processEmail function handle it
                // by checking if the email can be moved to processed-tasks
                const uid = msg.attributes?.uid;
                console.log(`📧 Passing UID ${uid} to processEmail`);
                processEmail(imap, stream, { uid: uid }).finally(() => {
                  pendingOperations--;
                  if (pendingOperations === 0) {
                    // Wait a bit for any pending move operations to complete
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
              // Don't end the connection here, wait for all operations to complete
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