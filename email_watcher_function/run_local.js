#!/usr/bin/env node

/**
 * Local email watcher runner
 * Continuously monitors Gmail for new emails from foilboi@gmail.com with "your new task from foilboi808" subject
 */

const { emailWatcher } = require('./index.js');

// Mock request and response objects for local testing
const mockRequest = {};
const mockResponse = {
  status: (code) => {
    console.log(`Response status: ${code}`);
    return mockResponse;
  },
  send: (message) => {
    console.log(`Response: ${message}`);
  }
};

async function runEmailWatcher() {
  console.log('🚀 Starting local email watcher...');
  console.log('📧 Monitoring Gmail for emails with "your new task" subject');
  console.log('🔄 Will check for new emails every 30 seconds');
  console.log('⏹️  Press Ctrl+C to stop');
  
  try {
    await emailWatcher(mockRequest, mockResponse);
  } catch (error) {
    console.error('❌ Error running email watcher:', error);
  }
}

async function runContinuous() {
  while (true) {
    try {
      console.log('\n🔄 Checking for new emails...');
      await runEmailWatcher();
      console.log('✅ Email check completed, waiting 30 seconds...');
      await new Promise(resolve => setTimeout(resolve, 30000)); // Wait 30 seconds
    } catch (error) {
      console.error('❌ Error in continuous loop:', error);
      console.log('⏳ Waiting 30 seconds before retrying...');
      await new Promise(resolve => setTimeout(resolve, 30000));
    }
  }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down email watcher...');
  process.exit(0);
});

// Start the continuous monitoring
runContinuous().catch(error => {
  console.error('❌ Fatal error:', error);
  process.exit(1);
}); 