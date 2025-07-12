const { google } = require('googleapis');
const fs = require('fs');

// Load credentials
const tokens = JSON.parse(fs.readFileSync('token.json'));
const credentials = JSON.parse(fs.readFileSync('credentials.json'));
const { client_id, client_secret } = credentials.installed;

// Create OAuth2 client
const oauth2Client = new google.auth.OAuth2(client_id, client_secret, 'http://localhost');
oauth2Client.setCredentials(tokens);

// Create sheets API instance
const sheets = google.sheets({ version: 'v4', auth: oauth2Client });

// Spreadsheet IDs
const CHARLESTON_SHEET_ID = '1pbfEpXk-yerQnjaMkML-dVkqcO-fnvu15M3GKcwMqEI';

async function exploreSheetStructure() {
  console.log('Exploring Charleston 2025 Forecast Sheet Structure...\n');
  
  try {
    // First, let's look at the "2025 Forecast" tab
    console.log('1. Reading 2025 Forecast tab headers...');
    const forecastHeaders = await sheets.spreadsheets.values.get({
      spreadsheetId: CHARLESTON_SHEET_ID,
      range: '2025 Forecast!A1:Z5',
    });
    
    console.log('   Headers:');
    if (forecastHeaders.data.values) {
      forecastHeaders.data.values.forEach((row, i) => {
        if (row.some(cell => cell)) {
          console.log(`   Row ${i + 1}: ${row.filter(cell => cell).join(' | ')}`);
        }
      });
    }
    
    // Look for monthly data
    console.log('\n2. Checking for monthly data in 2025 Forecast tab...');
    const monthlyData = await sheets.spreadsheets.values.get({
      spreadsheetId: CHARLESTON_SHEET_ID,
      range: '2025 Forecast!A1:N20',
    });
    
    if (monthlyData.data.values) {
      console.log('   Monthly columns found:');
      const headers = monthlyData.data.values[0] || [];
      headers.forEach((header, i) => {
        if (header) console.log(`   Col ${String.fromCharCode(65 + i)}: ${header}`);
      });
    }
    
    // Check a specific month tab (July 2025)
    console.log('\n3. Reading July 2025 tab structure...');
    const julyData = await sheets.spreadsheets.values.get({
      spreadsheetId: CHARLESTON_SHEET_ID,
      range: 'Jul 2025!A1:F30',
    });
    
    if (julyData.data.values) {
      console.log('   July 2025 data:');
      julyData.data.values.slice(0, 10).forEach((row, i) => {
        if (row.some(cell => cell)) {
          console.log(`   Row ${i + 1}: ${row.slice(0, 4).join(' | ')}`);
        }
      });
    }
    
    // Look for specific metrics
    console.log('\n4. Searching for key metrics (Revenue, Traffic, etc.)...');
    const searchRange = await sheets.spreadsheets.values.get({
      spreadsheetId: CHARLESTON_SHEET_ID,
      range: '2025 Forecast!A1:B50',
    });
    
    if (searchRange.data.values) {
      searchRange.data.values.forEach((row, i) => {
        const label = row[0];
        if (label && (
          label.toLowerCase().includes('revenue') ||
          label.toLowerCase().includes('sales') ||
          label.toLowerCase().includes('traffic') ||
          label.toLowerCase().includes('conversion') ||
          label.toLowerCase().includes('average') ||
          label.toLowerCase().includes('goal') ||
          label.toLowerCase().includes('forecast')
        )) {
          console.log(`   Row ${i + 1}: ${row.join(' | ')}`);
        }
      });
    }
    
  } catch (error) {
    console.error('Error exploring sheets:', error.message);
  }
}

exploreSheetStructure();