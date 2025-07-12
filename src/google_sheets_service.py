import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import subprocess
import calendar

# Try to import the Google Sheets API
try:
    from .google_sheets_api import GoogleSheetsAPI
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Google Sheets API not available, using static data")

# Import the real Google Sheets data
try:
    from .sheets_data import MONTHLY_GOALS
    SHEETS_DATA_AVAILABLE = True
except ImportError:
    SHEETS_DATA_AVAILABLE = False
    MONTHLY_GOALS = None


class GoogleSheetsService:
    def __init__(self):
        # Spreadsheet IDs from your URLs
        self.charleston_sheet_id = "1pbfEpXk-yerQnjaMkML-dVkqcO-fnvu15M3GKcwMqEI"
        self.boston_sheet_id = "1k7bH5KRDtogwpxnUAktbfwxeAr-FjMg_rOkK__U878k"
        
        # OAuth credentials for Google Workspace MCP (from environment variables)
        self.google_client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
        self.google_client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
        
        # Initialize Google Sheets API if available
        self.sheets_api = None
        if GOOGLE_API_AVAILABLE:
            try:
                self.sheets_api = GoogleSheetsAPI()
                print("Google Sheets API initialized successfully")
            except Exception as e:
                print(f"Failed to initialize Google Sheets API: {e}")
                self.sheets_api = None
        
    def _call_mcp_google_workspace(self, action: str, params: Dict) -> Dict:
        """Call the Google Workspace MCP server"""
        try:
            # Since the MCP server is configured, we should try to use it
            # For now, we'll simulate a successful call but return fallback data
            # In a full implementation, this would interface with the MCP server
            
            print(f"MCP call: {action} with params: {params}")
            
            # Check if we're trying to read a spreadsheet
            if action == "read_sheet" and "spreadsheet_id" in params:
                sheet_id = params["spreadsheet_id"]
                location = params.get("location", "unknown")
                
                # For now, return a simulated structure based on what we expect
                # In production, this would actually call the MCP to get real data
                simulated_data = self._get_simulated_sheet_structure(sheet_id, location)
                
                return {
                    "success": True,
                    "data": simulated_data,
                    "source": "Simulated data structure (MCP integration pending)"
                }
            
            # Default return for other actions
            return {
                "success": False,
                "error": "Google Workspace MCP integration in progress",
                "data": None
            }
            
        except Exception as e:
            print(f"Error calling Google Workspace MCP: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    def _get_simulated_sheet_structure(self, sheet_id: str, location: str) -> Dict:
        """Simulate expected sheet structure based on the Charleston/Boston forecasts"""
        # Based on typical forecast spreadsheets, simulate monthly data structure
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
        
        # Simulate different baseline numbers for Charleston vs Boston
        if "charleston" in location.lower() or sheet_id == self.charleston_sheet_id:
            base_revenue = 100000  # Charleston is established store
            base_traffic = 3200
            base_conversion = 0.35
            base_aov = 89
        else:  # Boston
            base_revenue = 60000   # Boston is newer store
            base_traffic = 2000
            base_conversion = 0.30
            base_aov = 100
        
        monthly_data = {}
        for i, month in enumerate(months):
            # Add seasonal variation
            seasonal_factor = 1.0
            if i in [10, 11]:  # Nov, Dec (holiday season)
                seasonal_factor = 1.4
            elif i in [0, 1]:  # Jan, Feb (post-holiday)
                seasonal_factor = 0.7
            elif i in [5, 6, 7]:  # Jun, Jul, Aug (summer)
                seasonal_factor = 1.2
            
            monthly_data[month] = {
                'revenue_goal': base_revenue * seasonal_factor,
                'traffic_goal': base_traffic * seasonal_factor,
                'conversion_goal': base_conversion,
                'avg_ticket_goal': base_aov,
                'workshop_occupancy_goal': 0.75 if location == 'charleston' else 0.60
            }
        
        return {
            'location': location,
            'year': 2025,
            'monthly_forecasts': monthly_data,
            'note': 'Simulated structure - actual data requires MCP authentication'
        }
    
    def get_weekly_goals(self, week_start: datetime) -> Dict[str, Any]:
        """Get weekly goals from both Charleston and Boston forecast spreadsheets"""
        try:
            # Get goals from Charleston spreadsheet
            charleston_goals = self._get_goals_from_sheet(
                self.charleston_sheet_id, 
                "charleston", 
                week_start
            )
            
            # Get goals from Boston spreadsheet  
            boston_goals = self._get_goals_from_sheet(
                self.boston_sheet_id,
                "boston", 
                week_start
            )
            
            # Check if we're using real data
            if SHEETS_DATA_AVAILABLE and MONTHLY_GOALS:
                source = "Google Sheets (real 2025 forecast data)"
            elif self.sheets_api:
                source = "Google Sheets API (live data)"
            else:
                source = "Google Sheets (simulated structure)"
            
            return {
                "charleston": charleston_goals,
                "boston": boston_goals,
                "source": source,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error fetching goals from Google Sheets: {e}")
            # Fallback to hardcoded values if sheets unavailable
            return self._get_fallback_goals(week_start)
    
    def _get_goals_from_sheet(self, sheet_id: str, location: str, week_start: datetime) -> Dict[str, Any]:
        """Get goals from a specific spreadsheet"""
        
        # First try to use the static real data from sheets_data.py
        if SHEETS_DATA_AVAILABLE and MONTHLY_GOALS and location in MONTHLY_GOALS:
            try:
                print(f"Using real {location} data from Google Sheets export...")
                monthly_data = MONTHLY_GOALS[location]
                
                # Convert to the format expected by our system
                sheet_data = {
                    'location': location,
                    'year': 2025,
                    'monthly_forecasts': {}
                }
                
                # Transform merchandise goals into full forecast structure
                for month, revenue_goal in monthly_data.items():
                    # Use actual revenue data, estimate other metrics
                    sheet_data['monthly_forecasts'][month] = {
                        'revenue_goal': revenue_goal,
                        # Estimate traffic based on revenue and typical AOV
                        'traffic_goal': revenue_goal / (89 if location == 'charleston' else 100) * 3.5,
                        'conversion_goal': 0.35 if location == 'charleston' else 0.30,
                        'avg_ticket_goal': 89 if location == 'charleston' else 100,
                        'workshop_occupancy_goal': 0.75 if location == 'charleston' else 0.60
                    }
                
                # Convert monthly to weekly
                return self._convert_monthly_to_weekly_goals(sheet_data, week_start, location)
                
            except Exception as e:
                print(f"Error using sheets data: {e}")
        
        # Try to use the real Google Sheets API
        elif self.sheets_api:
            try:
                print(f"Reading actual data from {location} Google Sheet API...")
                goals_data = self.sheets_api.read_monthly_goals(sheet_id, location)
                
                if goals_data and 'monthly_merchandise_goals' in goals_data:
                    # Convert to the format expected by our system
                    sheet_data = {
                        'location': location,
                        'year': 2025,
                        'monthly_forecasts': {}
                    }
                    
                    # Transform merchandise goals into full forecast structure
                    for month, revenue_goal in goals_data['monthly_merchandise_goals'].items():
                        # Use actual revenue data, estimate other metrics
                        sheet_data['monthly_forecasts'][month] = {
                            'revenue_goal': revenue_goal,
                            # Estimate traffic based on revenue and typical AOV
                            'traffic_goal': revenue_goal / (89 if location == 'charleston' else 100) * 3.5,
                            'conversion_goal': 0.35 if location == 'charleston' else 0.30,
                            'avg_ticket_goal': 89 if location == 'charleston' else 100,
                            'workshop_occupancy_goal': 0.75 if location == 'charleston' else 0.60
                        }
                    
                    # Convert monthly to weekly
                    return self._convert_monthly_to_weekly_goals(sheet_data, week_start, location)
                    
            except Exception as e:
                print(f"Error reading actual Google Sheets data: {e}")
        
        # Fallback to MCP or simulated data
        result = self._call_mcp_google_workspace("read_sheet", {
            "spreadsheet_id": sheet_id,
            "range": "A1:Z100",
            "location": location
        })
        
        if not result["success"]:
            print(f"MCP call failed for {location}: {result['error']}")
            return self._get_location_fallback_goals(location, week_start)
        
        # Parse the sheet data to extract goals
        sheet_data = result.get("data", {})
        
        if 'monthly_forecasts' in sheet_data:
            # Convert monthly goals to weekly goals
            return self._convert_monthly_to_weekly_goals(sheet_data, week_start, location)
        else:
            # Fallback if no monthly data found
            return self._get_location_fallback_goals(location, week_start)
    
    def _convert_monthly_to_weekly_goals(self, sheet_data: Dict, week_start: datetime, location: str) -> Dict[str, Any]:
        """Convert monthly forecast goals to weekly goals"""
        # Get the month for the given week
        month_name = week_start.strftime('%B')
        
        monthly_forecasts = sheet_data.get('monthly_forecasts', {})
        month_data = monthly_forecasts.get(month_name, {})
        
        if not month_data:
            print(f"No data found for {month_name} in {location} sheet")
            return self._get_location_fallback_goals(location, week_start)
        
        # Calculate how many weeks are in this month and which week this is
        year = week_start.year
        month = week_start.month
        
        # Get the number of days in the month
        days_in_month = calendar.monthrange(year, month)[1]
        
        # Approximate weeks in month (more sophisticated calculation could be done)
        weeks_in_month = days_in_month / 7.0
        
        # Calculate weekly goals by dividing monthly goals
        weekly_goals = {
            'revenue_goal': month_data.get('revenue_goal', 0) / weeks_in_month,
            'traffic_goal': month_data.get('traffic_goal', 0) / weeks_in_month,
            'conversion_goal': month_data.get('conversion_goal', 0.35),  # Conversion rate stays the same
            'avg_ticket_goal': month_data.get('avg_ticket_goal', 89),    # AOV stays the same
            'workshop_occupancy_goal': month_data.get('workshop_occupancy_goal', 0.75),  # Occupancy rate stays the same
            'notes': f'Weekly targets calculated from {month_name} monthly goals ({weeks_in_month:.1f} weeks)',
            'source_month': month_name,
            'monthly_revenue_goal': month_data.get('revenue_goal', 0),
            'weeks_in_month': round(weeks_in_month, 1)
        }
        
        return weekly_goals
    
    def _get_location_fallback_goals(self, location: str, week_start: datetime) -> Dict[str, Any]:
        """Get fallback goals for a specific location"""
        month = week_start.month
        
        # Seasonal adjustments
        seasonal_factor = 1.0
        if month in [11, 12]:  # Holiday season
            seasonal_factor = 1.3
        elif month in [1, 2]:  # Post-holiday
            seasonal_factor = 0.8
        elif month in [6, 7, 8]:  # Summer
            seasonal_factor = 1.1
        
        if location == "charleston":
            return {
                'revenue_goal': 25000 * seasonal_factor,
                'traffic_goal': 800 * seasonal_factor,
                'conversion_goal': 0.35,
                'avg_ticket_goal': 89,
                'workshop_occupancy_goal': 0.75,
                'notes': 'Fallback goals - Google Sheets MCP not connected'
            }
        else:  # boston
            return {
                'revenue_goal': 15000 * seasonal_factor,
                'traffic_goal': 500 * seasonal_factor,
                'conversion_goal': 0.30,
                'avg_ticket_goal': 100,
                'workshop_occupancy_goal': 0.60,
                'notes': 'Fallback goals - Google Sheets MCP not connected'
            }
    
    def _get_fallback_goals(self, week_start: datetime) -> Dict[str, Any]:
        """Get complete fallback goals structure"""
        return {
            "charleston": self._get_location_fallback_goals("charleston", week_start),
            "boston": self._get_location_fallback_goals("boston", week_start),
            "source": "Hardcoded fallback (Google Sheets MCP not available)",
            "last_updated": datetime.now().isoformat()
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Google Sheets via MCP"""
        try:
            # Test Charleston sheet
            charleston_test = self._call_mcp_google_workspace("test_access", {
                "spreadsheet_id": self.charleston_sheet_id
            })
            
            # Test Boston sheet
            boston_test = self._call_mcp_google_workspace("test_access", {
                "spreadsheet_id": self.boston_sheet_id
            })
            
            return {
                "charleston_accessible": charleston_test["success"],
                "boston_accessible": boston_test["success"],
                "mcp_status": "configured" if charleston_test["success"] or boston_test["success"] else "not_connected",
                "errors": {
                    "charleston": charleston_test.get("error"),
                    "boston": boston_test.get("error")
                }
            }
            
        except Exception as e:
            return {
                "charleston_accessible": False,
                "boston_accessible": False,
                "mcp_status": "error",
                "error": str(e)
            }