/**
 * WebSocket Connection Test Script
 *
 * HOW TO USE:
 * 1. Open browser and navigate to http://localhost:8080
 * 2. Login to the application
 * 3. Open Developer Tools (F12) → Console tab
 * 4. Copy and paste this entire script into the console
 * 5. Press Enter to run
 *
 * EXPECTED RESULT:
 * - "✅ WebSocket connected!" message
 * - Connection status will show as "OPEN"
 * - You should receive messages from the server
 *
 * TROUBLESHOOTING:
 * - If you see "❌ WebSocket failed to connect", check:
 *   1. Is Daphne running on port 8000? (ps aux | grep daphne)
 *   2. Are you logged in to the application?
 *   3. Check browser console for detailed error messages
 */

console.log('🧪 Starting WebSocket connection test...');

// WebSocket URL from frontend config
const wsUrl = 'ws://localhost:8000/ws/chat/general/';

console.log(`📡 Connecting to: ${wsUrl}`);

// Create WebSocket connection
const testWs = new WebSocket(wsUrl);

// Connection opened
testWs.onopen = function(event) {
  console.log('✅ WebSocket connected!');
  console.log('   Connection state:', testWs.readyState === WebSocket.OPEN ? 'OPEN' : 'UNKNOWN');

  // Send test message
  const testMessage = {
    type: 'chat_message',
    data: {
      content: 'Test message from browser console'
    }
  };

  testWs.send(JSON.stringify(testMessage));
  console.log('📤 Sent test message:', testMessage);
};

// Listen for messages
testWs.onmessage = function(event) {
  console.log('📨 Received message:',event.data);

  try {
    const message = JSON.parse(event.data);
    console.log('   Parsed message:', message);
  } catch (e) {
    console.error('   Failed to parse message:', e);
  }
};

// Connection closed
testWs.onclose = function(event) {
  console.log('🔌 WebSocket disconnected');
  console.log('   Close code:', event.code);
  console.log('   Close reason:', event.reason || 'No reason provided');

  if (event.code === 1006) {
    console.error('❌ Abnormal closure - possible causes:');
    console.error('   - Server not running (check Daphne)');
    console.error('   - Network error');
    console.error('   - Authentication failed (not logged in)');
  }
};

// Connection error
testWs.onerror = function(error) {
  console.error('❌ WebSocket error:', error);
  console.error('   Possible causes:');
  console.error('   - Daphne server not running on port 8000');
  console.error('   - CORS/Origin validation issue');
  console.error('   - Network connectivity problem');
};

console.log('⏳ Waiting for connection...');
console.log('   (This test WebSocket is stored in window.testWs)');
console.log('   To close: testWs.close()');

// Store in window for manual testing
window.testWs = testWs;
