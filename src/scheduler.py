import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from .shopify_service import ShopifyService
from .shopify_analytics import ShopifyAnalytics
from .conversational_insights import ConversationalInsights
from .shopify_report_generator import ShopifyReportGenerator
from .email_service import ConversationalEmailService
from .feedback_database import FeedbackDatabase
from .reply_processor import ReplyProcessor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShopifyScheduler:
    def __init__(self, app=None):
        self.scheduler = BackgroundScheduler()
        self.app = app
        self.email_service = None
        self.db = FeedbackDatabase()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        self.email_service = ConversationalEmailService(app)
        
        # Start the scheduler
        self.scheduler.start()
        
        # Schedule weekly report
        self._schedule_weekly_report()
        
        # Schedule reply processing every hour
        self._schedule_reply_processing()
        
        # Schedule daily Google Sheets refresh
        self._schedule_daily_sheets_refresh()
        
        logger.info("Shopify scheduler initialized")
    
    def _schedule_weekly_report(self):
        """Schedule the weekly report generation and sending"""
        # Get default schedule from environment
        day_of_week = int(os.getenv('WEEKLY_REPORT_DAY', '0'))  # 0 = Monday
        hour = int(os.getenv('WEEKLY_REPORT_HOUR', '8'))
        timezone = os.getenv('SCHEDULER_TIMEZONE', 'America/New_York')
        
        # Create cron trigger
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=0,
            timezone=pytz.timezone(timezone)
        )
        
        # Add job
        self.scheduler.add_job(
            func=self.generate_and_send_weekly_reports,
            trigger=trigger,
            id='weekly_shopify_report',
            replace_existing=True
        )
        
        logger.info(f"Weekly report scheduled for day {day_of_week} at {hour}:00 {timezone}")
    
    def _schedule_reply_processing(self):
        """Schedule email reply processing every 5 minutes"""
        self.scheduler.add_job(
            func=self.process_email_replies,
            trigger='interval',
            minutes=5,
            id='process_email_replies',
            replace_existing=True
        )
        
        logger.info("Email reply processing scheduled every 5 minutes")
    
    def _schedule_daily_sheets_refresh(self):
        """Schedule daily Google Sheets data refresh"""
        # Refresh at 3 AM daily
        hour = int(os.getenv('SHEETS_REFRESH_HOUR', '3'))
        timezone = os.getenv('SCHEDULER_TIMEZONE', 'America/New_York')
        
        trigger = CronTrigger(
            hour=hour,
            minute=0,
            timezone=pytz.timezone(timezone)
        )
        
        self.scheduler.add_job(
            func=self.refresh_google_sheets,
            trigger=trigger,
            id='daily_sheets_refresh',
            replace_existing=True
        )
        
        logger.info(f"Google Sheets refresh scheduled daily at {hour}:00 {timezone}")
    
    def refresh_google_sheets(self):
        """Refresh Google Sheets data"""
        logger.info("Running scheduled Google Sheets refresh")
        try:
            from .auto_refresh_sheets import AutoRefreshSheets
            refresher = AutoRefreshSheets()
            success = refresher.refresh_and_save()
            if success:
                logger.info("✅ Scheduled Google Sheets refresh completed successfully")
            else:
                logger.error("❌ Scheduled Google Sheets refresh failed")
        except Exception as e:
            logger.error(f"Error in scheduled sheets refresh: {e}")
    
    def generate_and_send_weekly_reports(self):
        """Generate and send weekly reports to all active recipients"""
        logger.info("Starting weekly report generation")
        
        try:
            # First, refresh Google Sheets data automatically
            try:
                from .auto_refresh_sheets import AutoRefreshSheets
                logger.info("Refreshing Google Sheets data before generating reports...")
                refresher = AutoRefreshSheets()
                refresher.refresh_and_save()
                logger.info("Google Sheets data refreshed successfully")
            except Exception as e:
                logger.warning(f"Could not refresh Google Sheets data: {e}")
                logger.info("Continuing with existing data...")
            
            # Initialize services
            shopify = ShopifyService()
            analytics = ShopifyAnalytics(shopify)
            insights_generator = ConversationalInsights()
            report_generator = ShopifyReportGenerator()
            
            # Get all active recipients
            recipients = self.db.get_all_active_recipients()
            
            if not recipients:
                logger.warning("No active recipients found")
                return
            
            # Generate analytics data
            analytics_data = analytics.analyze_weekly_data()
            
            # Process each recipient
            for recipient_email in recipients:
                try:
                    # Get recipient preferences and name
                    prefs = self.db.get_recipient_preferences(recipient_email)
                    recipient_name = prefs.get('name', recipient_email.split('@')[0])
                    
                    # Get feedback context for this recipient
                    feedback_context = self.db.get_feedback_context_for_email(recipient_email)
                    
                    # Generate personalized insights
                    ai_insights = insights_generator.generate_insights(
                        analytics_data, 
                        recipient_name,
                        feedback_context
                    )
                    
                    # Skip PDF generation to avoid timeouts
                    pdf_path = None
                    
                    # Send email
                    success = self.email_service.send_weekly_report(
                        recipient_email=recipient_email,
                        recipient_name=recipient_name,
                        analytics_data=analytics_data,
                        insights=ai_insights.get('insights_text', ai_insights.get('insights_html', '')),
                        questions=ai_insights.get('questions', []),
                        pdf_attachment=pdf_path
                    )
                    
                    if success:
                        # Save conversation history
                        self.db.save_conversation(
                            recipient_email=recipient_email,
                            report_date=analytics_data['week_start'],
                            insights=ai_insights.get('insights_text', ai_insights.get('insights_html', '')),
                            questions=ai_insights.get('questions', []),
                            pdf_path=pdf_path
                        )
                        
                        # Save enhanced memory
                        try:
                            from .memory_service import MemoryService
                            memory = MemoryService()
                            memory.save_enhanced_conversation(
                                recipient_email=recipient_email,
                                email_content=ai_insights.get('insights_text', ''),
                                analytics_data=analytics_data,
                                questions=ai_insights.get('questions', []),
                                topics=self._extract_topics_from_analytics(analytics_data)
                            )
                        except Exception as e:
                            logger.warning(f"Could not save enhanced memory: {e}")
                        
                        logger.info(f"Weekly report sent successfully to {recipient_email}")
                    else:
                        logger.error(f"Failed to send report to {recipient_email}")
                
                except Exception as e:
                    logger.error(f"Error processing recipient {recipient_email}: {str(e)}")
                    continue
            
            # Close Shopify session
            shopify.close_session()
            
        except Exception as e:
            logger.error(f"Error in weekly report generation: {str(e)}")
            
            # Send error notification
            if self.email_service:
                self.email_service.send_error_notification(str(e))
    
    def process_email_replies(self):
        """Process incoming email replies"""
        logger.info("Processing email replies")
        
        try:
            processor = ReplyProcessor()
            replies = processor.process_replies()
            
            if replies:
                logger.info(f"Processed {len(replies)} email replies")
                
                # Count how many responses were sent
                responses_sent = sum(1 for reply in replies if reply.get('response_sent', False))
                if responses_sent > 0:
                    logger.info(f"Sophie sent {responses_sent} automated responses")
                
                # Update preferences based on feedback
                for reply in replies:
                    processor.update_preferences_from_feedback(
                        reply['sender'],
                        reply['context']
                    )
            
        except Exception as e:
            logger.error(f"Error processing email replies: {str(e)}")
    
    def trigger_manual_report(self, recipient_email: str, recipient_name: str = None) -> Dict:
        """Manually trigger a report for a specific recipient"""
        try:
            # Initialize services
            shopify = ShopifyService()
            analytics = ShopifyAnalytics(shopify)
            insights_generator = ConversationalInsights()
            report_generator = ShopifyReportGenerator()
            
            # Generate analytics data
            analytics_data = analytics.analyze_weekly_data()
            
            # Get feedback context
            feedback_context = self.db.get_feedback_context_for_email(recipient_email)
            
            # Use provided name or get from preferences
            if not recipient_name:
                prefs = self.db.get_recipient_preferences(recipient_email)
                recipient_name = prefs.get('name', recipient_email.split('@')[0])
            
            # Generate insights
            ai_insights = insights_generator.generate_insights(
                analytics_data,
                recipient_name,
                feedback_context
            )
            
            # Skip PDF generation to avoid timeouts
            pdf_path = None
            
            # Send email
            success = self.email_service.send_weekly_report(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                analytics_data=analytics_data,
                insights=ai_insights.get('insights_text', ai_insights.get('insights_html', '')),
                questions=ai_insights.get('questions', []),
                pdf_attachment=pdf_path
            )
            
            if success:
                # Save conversation history
                self.db.save_conversation(
                    recipient_email=recipient_email,
                    report_date=analytics_data['week_start'],
                    insights=ai_insights.get('insights_text', ai_insights.get('insights_html', '')),
                    questions=ai_insights.get('questions', []),
                    pdf_path=pdf_path
                )
            
            # Close Shopify session
            shopify.close_session()
            
            return {
                'success': success,
                'analytics_data': analytics_data,
                'insights': ai_insights,
                'pdf_path': pdf_path
            }
            
        except Exception as e:
            logger.error(f"Error generating manual report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_topics_from_analytics(self, analytics_data: Dict) -> List[str]:
        """Extract key topics from analytics data"""
        topics = []
        
        # Revenue performance
        yoy = analytics_data.get('yoy_changes', {})
        if yoy.get('total_revenue_change', 0) > 20:
            topics.append("strong revenue growth")
        elif yoy.get('total_revenue_change', 0) < -10:
            topics.append("revenue challenges")
            
        # Store performance
        charleston = analytics_data.get('current_week_by_location', {}).get('charleston', {})
        boston = analytics_data.get('current_week_by_location', {}).get('boston', {})
        
        if charleston.get('total_revenue', 0) > boston.get('total_revenue', 0) * 3:
            topics.append("charleston outperformance")
        
        # Products
        products = analytics_data.get('product_performance', [])
        if products:
            topics.append(f"top: {products[0]['product']}")
            
        # Workshops
        workshops = analytics_data.get('workshop_analytics', {})
        if workshops.get('attendees', 0) > 50:
            topics.append("strong workshop attendance")
            
        return topics
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down")