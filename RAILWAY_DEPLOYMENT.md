# Railway Deployment Instructions

## Manual Deployment Steps

Since the Railway API is having issues, please follow these manual steps to deploy:

### 1. Login to Railway
Go to [https://railway.app](https://railway.app) and login with your account.

### 2. Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Connect to GitHub if not already connected
4. Select the repository: `rewined/shopify-weekly-summary`
5. Select the `main` branch

### 3. Configure Environment Variables
Click on the service and go to the "Variables" tab. Add all these environment variables:

```
SHOPIFY_SHOP_DOMAIN=(get from .env file)
SHOPIFY_ACCESS_TOKEN=(get from .env file)
SHOPIFY_API_KEY=(get from .env file)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=(get from .env file)
MAIL_PASSWORD=(get from .env file)
MAIL_DEFAULT_SENDER=(get from .env file)
EMAIL_RECIPIENTS=(get from .env file)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=(get from .env file)
IMAP_PASSWORD=(get from .env file)
ANTHROPIC_API_KEY=(get from .env file)
SCHEDULER_TIMEZONE=America/New_York
WEEKLY_REPORT_HOUR=8
WEEKLY_REPORT_DAY=0
FLASK_SECRET_KEY=(generate a secure key)
DATABASE_PATH=data/feedback.db
```

**Important**: The actual values for these environment variables have been provided separately. Do not commit sensitive data to the repository.

### 4. Deploy
1. Railway will automatically start building and deploying
2. Wait for the build to complete (usually 2-3 minutes)
3. Once deployed, Railway will provide a URL

### 5. Get the Deployment URL
1. In the service settings, go to "Settings" tab
2. Under "Domains", click "Generate Domain"
3. Copy the generated URL (e.g., `https://shopify-weekly-summary-production.up.railway.app`)

### 6. Test the Deployment
1. Visit the deployment URL
2. Try sending a test email
3. Check the logs in Railway if there are any issues

## Auto-Deploy Setup
Railway will automatically deploy new changes when you push to the `main` branch on GitHub.

## Monitoring
- Check the "Logs" tab in Railway for real-time logs
- Monitor the "Metrics" tab for resource usage
- Set up alerts in the "Settings" tab if needed

## Troubleshooting
- If the build fails, check the build logs
- If the app crashes, check the runtime logs
- Ensure all environment variables are set correctly
- The health check endpoint is at `/health`