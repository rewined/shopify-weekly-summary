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
const BOSTON_SHEET_ID = '1k7bH5KRDtogwpxnUAktbfwxeAr-FjMg_rOkK__U878k';

async function readForecastData() {
  console.log('Reading 2025 Forecast Goals...\n');
  
  try {
    // Charleston 2025 Goals - starting around row 34
    console.log('1. Charleston 2025 Goals:');
    const charlestonGoals = await sheets.spreadsheets.values.get({
      spreadsheetId: CHARLESTON_SHEET_ID,
      range: '2025 Forecast!A30:N50',
    });
    
    if (charlestonGoals.data.values) {
      // Find the 2025 Goal section
      let goalStartRow = -1;
      charlestonGoals.data.values.forEach((row, i) => {
        if (row[0] && row[0].includes('2025 Goal')) {
          goalStartRow = i;
        }
      });
      
      if (goalStartRow >= 0) {
        console.log('   Found 2025 Goals section:');
        // Print the next 10 rows after finding 2025 Goal
        for (let i = goalStartRow; i < Math.min(goalStartRow + 10, charlestonGoals.data.values.length); i++) {
          const row = charlestonGoals.data.values[i];
          if (row[0]) {
            console.log(`   ${row[0]}: ${row.slice(1, 13).join(' | ')}`);
          }
        }
      }
    }
    
    // Boston 2025 Goals
    console.log('\n2. Boston 2025 Goals:');
    const bostonGoals = await sheets.spreadsheets.values.get({
      spreadsheetId: BOSTON_SHEET_ID,
      range: '2025 Forecast!A30:N50',
    });
    
    if (bostonGoals.data.values) {
      // Find the 2025 Goal section
      let goalStartRow = -1;
      bostonGoals.data.values.forEach((row, i) => {
        if (row[0] && row[0].includes('2025 Goal')) {
          goalStartRow = i;
        }
      });
      
      if (goalStartRow >= 0) {
        console.log('   Found 2025 Goals section:');
        // Print the next 10 rows
        for (let i = goalStartRow; i < Math.min(goalStartRow + 10, bostonGoals.data.values.length); i++) {
          const row = bostonGoals.data.values[i];
          if (row[0]) {
            console.log(`   ${row[0]}: ${row.slice(1, 13).join(' | ')}`);
          }
        }
      }
    }
    
    // Also check for daily goals in monthly tabs
    console.log('\n3. Sample Daily Goals from July 2025 (Charleston):');
    const julyDaily = await sheets.spreadsheets.values.get({
      spreadsheetId: CHARLESTON_SHEET_ID,
      range: 'Jul 2025!A1:G35',
    });
    
    if (julyDaily.data.values) {
      // Look for monthly totals
      julyDaily.data.values.forEach((row, i) => {
        if (row[0] && (row[0].includes('Total') || row[0].includes('Goal'))) {
          console.log(`   Row ${i + 1}: ${row.slice(0, 5).join(' | ')}`);
        }
      });
    }
    
  } catch (error) {
    console.error('Error reading goals:', error.message);
  }
}

readForecastData();