const fs = require('fs');
const { google } = require('googleapis');

// Get auth code from command line
const authCode = process.argv[2];

if (!authCode) {
  console.error('Please provide the authorization code as an argument');
  console.error('Usage: node exchange-code.js AUTH_CODE');
  process.exit(1);
}

// Read credentials
const credentials = JSON.parse(fs.readFileSync('credentials.json'));
const { client_id, client_secret, redirect_uris } = credentials.installed || credentials.web;

// Create OAuth2 client
const oauth2Client = new google.auth.OAuth2(
  client_id,
  client_secret,
  redirect_uris[0]
);

// Exchange code for tokens
oauth2Client.getToken(authCode, (err, tokens) => {
  if (err) {
    console.error('Error exchanging code for tokens:', err);
    return;
  }

  console.log('Successfully obtained tokens!');
  console.log('\nRefresh Token:', tokens.refresh_token);
  
  // Save tokens
  fs.writeFileSync('token.json', JSON.stringify(tokens, null, 2));
  console.log('\nTokens saved to token.json');
  
  console.log('\nAdd these environment variables to your MCP configuration:');
  console.log(`GOOGLE_CLIENT_ID=${client_id}`);
  console.log(`GOOGLE_CLIENT_SECRET=${client_secret}`);
  console.log(`GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}`);
});