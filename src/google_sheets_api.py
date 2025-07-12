import os
import json
from typing import Dict, Any, List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime

class GoogleSheetsAPI:
    """Direct Google Sheets API access for reading forecast data"""
    
    def __init__(self):
        # Load tokens
        token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
        with open(token_path, 'r') as f:
            token_data = json.load(f)
        
        # Create credentials from environment variables
        self.creds = Credentials(
            token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
        )
        
        # Build sheets service
        self.service = build('sheets', 'v4', credentials=self.creds)
        
        # Spreadsheet IDs
        self.charleston_sheet_id = "1pbfEpXk-yerQnjaMkML-dVkqcO-fnvu15M3GKcwMqEI"
        self.boston_sheet_id = "1k7bH5KRDtogwpxnUAktbfwxeAr-FjMg_rOkK__U878k"
    
    def read_monthly_goals(self, sheet_id: str, location: str) -> Dict[str, Any]:
        """Read monthly goals from the 2025 Forecast tab"""
        try:
            # Read the forecast data
            range_name = '2025 Forecast!A30:N50'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
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
            
            # Find merchandise sales row (usually 2 rows after the header)
            for i in range(goal_row_index + 1, min(goal_row_index + 10, len(values))):
                row = values[i]
                if row and row[0] and 'Merchandise' in row[0]:
                    # Extract monthly values (columns B through M)
                    for month_idx, month_name in enumerate(months):
                        if month_idx + 1 < len(row) and row[month_idx + 1]:
                            # Clean the value (remove $ and commas)
                            value_str = row[month_idx + 1].replace('$', '').replace(',', '')
                            try:
                                monthly_goals[month_name] = float(value_str)
                            except ValueError:
                                monthly_goals[month_name] = 0
                    break
            
            return {
                'location': location,
                'source': 'Google Sheets API',
                'monthly_merchandise_goals': monthly_goals,
                'sheet_id': sheet_id
            }
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
    
    def get_all_monthly_goals(self) -> Dict[str, Any]:
        """Get monthly goals for both Charleston and Boston"""
        charleston_data = self.read_monthly_goals(self.charleston_sheet_id, 'charleston')
        boston_data = self.read_monthly_goals(self.boston_sheet_id, 'boston')
        
        return {
            'charleston': charleston_data,
            'boston': boston_data,
            'timestamp': datetime.now().isoformat()
        }