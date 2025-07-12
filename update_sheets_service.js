const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

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

async function readMonthlyGoals(sheetId, location) {
  try {
    // Read the forecast data
    const result = await sheets.spreadsheets.values.get({
      spreadsheetId: sheetId,
      range: '2025 Forecast!A30:N50',
    });
    
    const values = result.data.values || [];
    
    // Find the 2025 Goal row
    let goalRowIndex = -1;
    for (let i = 0; i < values.length; i++) {
      if (values[i][0] && values[i][0].includes('2025 Goal')) {
        goalRowIndex = i;
        break;
      }
    }
    
    if (goalRowIndex === -1) {
      throw new Error(`Could not find 2025 Goal section in ${location} sheet`);
    }
    
    // Extract monthly merchandise sales goals
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December'];
    
    const monthlyGoals = {};
    
    // Find merchandise sales row - it's typically 3 rows after the goal header
    // Look for a row that starts with "Sales" and has "Merchandise" in column B
    for (let i = goalRowIndex + 1; i < Math.min(goalRowIndex + 10, values.length); i++) {
      const row = values[i];
      if (row && row[0] === 'Sales' && row[1] === 'Merchandise') {
        // Extract monthly values (columns C through N for Jan-Dec)
        for (let monthIdx = 0; monthIdx < months.length; monthIdx++) {
          if (monthIdx + 2 < row.length && row[monthIdx + 2]) {
            // Clean the value (remove $ and commas)
            const valueStr = row[monthIdx + 2].replace('$', '').replace(',', '');
            monthlyGoals[months[monthIdx]] = parseFloat(valueStr) || 0;
          }
        }
        break;
      }
    }
    
    return monthlyGoals;
    
  } catch (error) {
    console.error(`Error reading ${location} goals:`, error);
    return null;
  }
}

async function generateGoalsModule() {
  console.log('Generating JavaScript module with real Google Sheets data...\n');
  
  // Read goals from both sheets
  const charlestonGoals = await readMonthlyGoals(CHARLESTON_SHEET_ID, 'Charleston');
  const bostonGoals = await readMonthlyGoals(BOSTON_SHEET_ID, 'Boston');
  
  console.log('Charleston 2025 Monthly Goals:');
  console.log(charlestonGoals);
  
  console.log('\nBoston 2025 Monthly Goals:');
  console.log(bostonGoals);
  
  // Generate JavaScript module
  const moduleContent = `// Auto-generated from Google Sheets on ${new Date().toISOString()}
// Charleston: ${CHARLESTON_SHEET_ID}
// Boston: ${BOSTON_SHEET_ID}

const MONTHLY_GOALS = {
  charleston: ${JSON.stringify(charlestonGoals, null, 2)},
  boston: ${JSON.stringify(bostonGoals, null, 2)}
};

module.exports = { MONTHLY_GOALS };
`;
  
  // Write to file
  const outputPath = path.join(__dirname, 'src', 'sheets_data.js');
  fs.writeFileSync(outputPath, moduleContent);
  console.log(`\nGenerated ${outputPath}`);
  
  // Also update the Python file
  const pythonContent = `# Auto-generated from Google Sheets on ${new Date().toISOString()}
# Charleston: ${CHARLESTON_SHEET_ID}
# Boston: ${BOSTON_SHEET_ID}

MONTHLY_GOALS = {
    'charleston': ${JSON.stringify(charlestonGoals, null, 4).replace(/"/g, "'")},
    'boston': ${JSON.stringify(bostonGoals, null, 4).replace(/"/g, "'")}
}
`;
  
  const pythonPath = path.join(__dirname, 'src', 'sheets_data.py');
  fs.writeFileSync(pythonPath, pythonContent);
  console.log(`Generated ${pythonPath}`);
}

generateGoalsModule();