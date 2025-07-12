# 🚀 Fully Automatic Sophie Setup

This app is now configured to run completely hands-free. Once deployed to Railway, Sophie will:

## 🤖 What Happens Automatically

1. **On Startup:**
   - Refreshes Google Sheets data from your forecast spreadsheets
   - Sets up default recipients from environment variables
   - Initializes all scheduled tasks

2. **Every Week (Monday 8 AM by default):**
   - Refreshes latest Google Sheets goals
   - Analyzes Shopify data for the past week
   - Generates personalized emails for each recipient
   - Sends reports automatically

3. **Every Day (3 AM):**
   - Refreshes Google Sheets data to catch any forecast updates

4. **Every Hour:**
   - Processes email replies and feedback

## 🔧 One-Time Railway Setup

1. **Deploy to Railway:**
   ```bash
   git add .
   git commit -m "Full automation setup"
   git push
   ```

2. **Set Environment Variables in Railway:**
   Copy all variables from `.env.railway` to your Railway service:
   - All the Shopify credentials
   - Email settings (MAIL_USERNAME, MAIL_PASSWORD)
   - Google credentials (already included)
   - ANTHROPIC_API_KEY
   - DEFAULT_RECIPIENTS (comma-separated emails)

3. **That's it!** Sophie will:
   - Start automatically
   - Refresh your Google Sheets data
   - Send weekly reports on schedule
   - Update goals when you change your spreadsheets

## 📅 Customizing the Schedule

In Railway environment variables:
- `WEEKLY_REPORT_DAY`: 0=Monday, 1=Tuesday, etc. (default: 0)
- `WEEKLY_REPORT_HOUR`: Hour in 24-hour format (default: 8 = 8 AM)
- `SCHEDULER_TIMEZONE`: Your timezone (default: America/New_York)
- `SHEETS_REFRESH_HOUR`: Daily refresh hour (default: 3 = 3 AM)

## 📊 Your Google Sheets

Sophie automatically reads from:
- **Charleston**: `1pbfEpXk-yerQnjaMkML-dVkqcO-fnvu15M3GKcwMqEI`
- **Boston**: `1k7bH5KRDtogwpxnUAktbfwxeAr-FjMg_rOkK__U878k`

She looks for "2025 Goal" section and extracts monthly merchandise sales goals.

## 🔍 Monitoring

Visit your Railway app URL to:
- `/health` - Check if app is running
- `/test-analytics` - Test data fetching
- `/test-google-sheets` - Verify sheets connection

## 🎯 Zero Maintenance Required

Once set up, Sophie will:
- ✅ Keep goals updated from your spreadsheets
- ✅ Send reports on schedule
- ✅ Handle all data refreshing
- ✅ Process feedback automatically
- ✅ Never need manual intervention

Just update your Google Sheets forecasts, and Sophie will automatically use the new numbers!