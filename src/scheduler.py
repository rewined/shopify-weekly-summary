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
        """Schedule hourly email reply processing"""
        self.scheduler.add_job(
            func=self.process_email_replies,
            trigger='interval',
            hours=1,
            id='process_email_replies',
            replace_existing=True
        )
        
        logger.info("Email reply processing scheduled every hour")
    
    def generate_and_send_weekly_reports(self):
        """Generate and send weekly reports to all active recipients"""
        logger.info("Starting weekly report generation")
        
        try:
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
                    
                    # Generate PDF report
                    pdf_path = report_generator.generate_report(
                        analytics_data,
                        ai_insights.get('insights_text', ai_insights.get('insights_html', ''))
                    )
                    
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
            
            # Generate PDF
            pdf_path = report_generator.generate_report(
                analytics_data,
                ai_insights.get('insights_text', ai_insights.get('insights_html', ''))
            )
            
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
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down")