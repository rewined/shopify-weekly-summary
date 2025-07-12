const { google } = require('googleapis');
const fs = require('fs');

// Load the saved tokens
const tokens = JSON.parse(fs.readFileSync('token.json'));
const credentials = JSON.parse(fs.readFileSync('credentials.json'));
const { client_id, client_secret } = credentials.installed;

// Create OAuth2 client
const oauth2Client = new google.auth.OAuth2(
  client_id,
  client_secret,
  'http://localhost'
);

// Set credentials
oauth2Client.setCredentials(tokens);

// Create sheets API instance
const sheets = google.sheets({ version: 'v4', auth: oauth2Client });

// Spreadsheet IDs
const CHARLESTON_SHEET_ID = '1pbfEpXk-yerQnjaMkML-dVkqcO-fnvu15M3GKcwMqEI';
const BOSTON_SHEET_ID = '1k7bH5KRDtogwpxnUAktbfwxeAr-FjMg_rOkK__U878k';

async function testSheetsAccess() {
  console.log('Testing Google Sheets API access...\n');
  
  try {
    // Test Charleston sheet
    console.log('1. Fetching Charleston forecast sheet...');
    const charlestonResponse = await sheets.spreadsheets.get({
      spreadsheetId: CHARLESTON_SHEET_ID,
    });
    console.log(`   ✓ Title: ${charlestonResponse.data.properties.title}`);
    console.log(`   ✓ Sheets: ${charlestonResponse.data.sheets.map(s => s.properties.title).join(', ')}`);
    
    // Test Boston sheet
    console.log('\n2. Fetching Boston forecast sheet...');
    const bostonResponse = await sheets.spreadsheets.get({
      spreadsheetId: BOSTON_SHEET_ID,
    });
    console.log(`   ✓ Title: ${bostonResponse.data.properties.title}`);
    console.log(`   ✓ Sheets: ${bostonResponse.data.sheets.map(s => s.properties.title).join(', ')}`);
    
    // Try to read some data from Charleston
    console.log('\n3. Reading sample data from Charleston sheet...');
    const dataResponse = await sheets.spreadsheets.values.get({
      spreadsheetId: CHARLESTON_SHEET_ID,
      range: 'A1:Z10', // First 10 rows
    });
    
    if (dataResponse.data.values) {
      console.log('   ✓ Sample data:');
      dataResponse.data.values.slice(0, 3).forEach((row, i) => {
        console.log(`     Row ${i + 1}: ${row.slice(0, 5).join(' | ')}`);
      });
    }
    
    console.log('\n✅ Google Sheets API access successful!');
    console.log('Sophie can now read your actual forecast data.');
    
  } catch (error) {
    console.error('Error accessing Google Sheets:', error.message);
    if (error.code === 403) {
      console.error('Permission denied. Make sure the sheets are shared with the authenticated account.');
    }
  }
}

testSheetsAccess();