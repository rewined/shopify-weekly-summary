const { google } = require('googleapis');
const { authenticate } = require('@google-cloud/local-auth');
const fs = require('fs');
const path = require('path');

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/calendar',
  'https://www.googleapis.com/auth/gmail.send',
  'https://www.googleapis.com/auth/spreadsheets.readonly'
];

const TOKEN_PATH = path.join(__dirname, 'token.json');
const CREDENTIALS_PATH = path.join(__dirname, 'credentials.json');

async function authorize() {
  try {
    const client = await authenticate({
      scopes: SCOPES,
      keyfilePath: CREDENTIALS_PATH,
    });
    
    if (client.credentials) {
      await saveCredentials(client);
      console.log('Authorization successful!');
      console.log('\nYour refresh token:', client.credentials.refresh_token);
      console.log('\nAdd these environment variables to your MCP configuration:');
      console.log(`GOOGLE_CLIENT_ID=${client._clientId}`);
      console.log(`GOOGLE_CLIENT_SECRET=${client._clientSecret}`);
      console.log(`GOOGLE_REFRESH_TOKEN=${client.credentials.refresh_token}`);
    }
    
    return client;
  } catch (error) {
    console.error('Authorization failed:', error);
  }
}

async function saveCredentials(client) {
  const content = await fs.promises.readFile(CREDENTIALS_PATH);
  const keys = JSON.parse(content);
  const key = keys.web || keys.installed;
  const payload = JSON.stringify({
    type: 'authorized_user',
    client_id: key.client_id,
    client_secret: key.client_secret,
    refresh_token: client.credentials.refresh_token,
  });
  await fs.promises.writeFile(TOKEN_PATH, payload);
}

// Run the authorization
authorize();