import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_automatic_operations():
    """Set up all automatic operations on startup"""
    logger.info("=== Starting Automatic Setup ===")
    
    # 1. Check and set default recipients if not exists
    default_recipients = os.environ.get('DEFAULT_RECIPIENTS', 'adam@rewined.com').split(',')
    
    try:
        from .feedback_database import FeedbackDatabase
        db = FeedbackDatabase()
        
        # Add default recipients if they don't exist
        for email in default_recipients:
            if email.strip():
                existing = db.get_recipient_preferences(email.strip())
                if not existing:
                    db.save_recipient_preferences(email.strip(), {
                        'name': email.split('@')[0].title(),
                        'active': True,
                        'created_at': datetime.now().isoformat()
                    })
                    logger.info(f"Added default recipient: {email}")
    except Exception as e:
        logger.error(f"Error setting up recipients: {e}")
    
    # 2. Refresh Google Sheets data on startup
    try:
        from .auto_refresh_sheets import AutoRefreshSheets
        logger.info("Refreshing Google Sheets data on startup...")
        refresher = AutoRefreshSheets()
        refresher.refresh_and_save()
        logger.info("✅ Google Sheets data refreshed")
    except Exception as e:
        logger.warning(f"Could not refresh Google Sheets data on startup: {e}")
    
    # 3. Log scheduler configuration
    logger.info("=== Scheduler Configuration ===")
    logger.info(f"Weekly Report Day: {os.environ.get('WEEKLY_REPORT_DAY', '0')} (0=Monday)")
    logger.info(f"Weekly Report Hour: {os.environ.get('WEEKLY_REPORT_HOUR', '8')}:00")
    logger.info(f"Timezone: {os.environ.get('SCHEDULER_TIMEZONE', 'America/New_York')}")
    logger.info(f"Default Recipients: {default_recipients}")
    
    logger.info("=== Automatic Setup Complete ===")
    logger.info("Sophie is now running fully automatically!")
    logger.info("She will:")
    logger.info("  ✅ Refresh Google Sheets data before each report")
    logger.info("  ✅ Send weekly emails on schedule")
    logger.info("  ✅ Process replies every hour")
    logger.info("  ✅ Use your actual forecast data from spreadsheets")

if __name__ == "__main__":
    setup_automatic_operations()