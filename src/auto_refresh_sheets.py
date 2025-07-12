import os
import json
import subprocess
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoRefreshSheets:
    """Automatically refresh Google Sheets data without manual intervention"""
    
    def __init__(self):
        self.charleston_sheet_id = "1pbfEpXk-yerQnjaMkML-dVkqcO-fnvu15M3GKcwMqEI"
        self.boston_sheet_id = "1k7bH5KRDtogwpxnUAktbfwxeAr-FjMg_rOkK__U878k"
        self.creds = None
        self.service = None
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Set up Google credentials from environment or file"""
        # First try environment variables (for Railway)
        refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN')
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        
        if refresh_token and client_id and client_secret:
            logger.info("Using Google credentials from environment variables")
            self.creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret
            )
        else:
            # Fall back to token.json file
            token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
            if os.path.exists(token_path):
                logger.info("Using Google credentials from token.json")
                with open(token_path, 'r') as f:
                    token_data = json.load(f)
                self.creds = Credentials(
                    token=token_data.get('access_token'),
                    refresh_token=token_data.get('refresh_token'),
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
                    client_secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
                )
            else:
                raise Exception("No Google credentials found in environment or token.json")
        
        # Build the service
        self.service = build('sheets', 'v4', credentials=self.creds)
    
    def read_monthly_goals(self, sheet_id, location):
        """Read monthly goals from a spreadsheet"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='2025 Forecast!A30:N50',
            ).execute()
            
            values = result.get('values', [])
            
            # Find the 2025 Goal row
            goal_row_index = -1
            for i, row in enumerate(values):
                if row and row[0] and '2025 Goal' in row[0]:
                    goal_row_index = i
                    break
            
            if goal_row_index == -1:
                raise ValueError(f"Could not find 2025 Goal section in {location} sheet")
            
            # Extract monthly merchandise sales goals
            months = ['January', 'February', 'March', 'April', 'May', 'June', 
                     'July', 'August', 'September', 'October', 'November', 'December']
            
            monthly_goals = {}
            
            # Find merchandise sales row
            for i in range(goal_row_index + 1, min(goal_row_index + 10, len(values))):
                row = values[i]
                if row and len(row) > 1 and row[0] == 'Sales' and row[1] == 'Merchandise':
                    # Extract monthly values (columns C through N for Jan-Dec)
                    for month_idx, month_name in enumerate(months):
                        if month_idx + 2 < len(row) and row[month_idx + 2]:
                            value_str = row[month_idx + 2].replace('$', '').replace(',', '')
                            monthly_goals[month_name] = float(value_str) if value_str else 0
                    break
            
            return monthly_goals
            
        except Exception as e:
            logger.error(f"Error reading {location} goals: {e}")
            return {}
    
    def refresh_and_save(self):
        """Refresh data from Google Sheets and save to sheets_data.py"""
        logger.info(f"Starting automatic data refresh at {datetime.now()}")
        
        try:
            # Read goals from both sheets
            charleston_goals = self.read_monthly_goals(self.charleston_sheet_id, 'Charleston')
            boston_goals = self.read_monthly_goals(self.boston_sheet_id, 'Boston')
            
            if not charleston_goals or not boston_goals:
                logger.error("Failed to read goals from one or both sheets")
                return False
            
            # Generate Python module content
            python_content = f'''# Auto-generated from Google Sheets on {datetime.now().isoformat()}
# Charleston: {self.charleston_sheet_id}
# Boston: {self.boston_sheet_id}

MONTHLY_GOALS = {{
    'charleston': {json.dumps(charleston_goals, indent=4).replace('"', "'")},
    'boston': {json.dumps(boston_goals, indent=4).replace('"', "'")}
}}
'''
            
            # Save to file
            output_path = os.path.join(os.path.dirname(__file__), 'sheets_data.py')
            with open(output_path, 'w') as f:
                f.write(python_content)
            
            logger.info(f"Successfully updated {output_path}")
            logger.info(f"Charleston goals: {list(charleston_goals.keys())}")
            logger.info(f"Boston goals: {list(boston_goals.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during refresh: {e}")
            return False

def main():
    """Main function to run the refresh"""
    refresher = AutoRefreshSheets()
    success = refresher.refresh_and_save()
    
    if success:
        logger.info("✅ Google Sheets data refreshed successfully!")
    else:
        logger.error("❌ Failed to refresh Google Sheets data")
        # Don't crash - use existing data
    
    return success

if __name__ == "__main__":
    main()