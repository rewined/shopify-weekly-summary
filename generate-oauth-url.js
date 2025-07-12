const fs = require('fs');
const { google } = require('googleapis');

// Read credentials
const credentials = JSON.parse(fs.readFileSync('credentials.json'));
const { client_id, client_secret, redirect_uris } = credentials.installed || credentials.web;

// Create OAuth2 client
const oauth2Client = new google.auth.OAuth2(
  client_id,
  client_secret,
  redirect_uris[0]
);

// Generate auth URL
const SCOPES = [
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/calendar',
  'https://www.googleapis.com/auth/gmail.send',
  'https://www.googleapis.com/auth/spreadsheets.readonly'
];

const authUrl = oauth2Client.generateAuthUrl({
  access_type: 'offline',
  scope: SCOPES,
  prompt: 'consent'
});

console.log('Google OAuth Authorization URL:');
console.log('================================');
console.log(authUrl);
console.log('================================');
console.log('\nInstructions:');
console.log('1. Open the URL above in your browser');
console.log('2. Sign in with your Google account');
console.log('3. Grant the requested permissions');
console.log('4. You will be redirected to http://localhost?code=AUTH_CODE');
console.log('5. Copy the AUTH_CODE from the URL');
console.log('6. Run: node exchange-code.js AUTH_CODE');