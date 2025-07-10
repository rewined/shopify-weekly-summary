import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file
from src.shopify_service import ShopifyService
from src.shopify_analytics import ShopifyAnalytics
from src.conversational_insights import ConversationalInsights
from src.shopify_report_generator import ShopifyReportGenerator
from src.email_service import ConversationalEmailService
from src.feedback_database import FeedbackDatabase
from src.reply_processor import ReplyProcessor
from src.scheduler import ReportScheduler
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'shopify-weekly-summary-secret-2024')

# Initialize services
shopify_service = ShopifyService()
analytics = ShopifyAnalytics(shopify_service)
insights = ConversationalInsights()
report_generator = ShopifyReportGenerator()
email_service = ConversationalEmailService()
feedback_db = FeedbackDatabase()
reply_processor = ReplyProcessor(feedback_db)

# Initialize scheduler
scheduler = ReportScheduler(
    shopify_service=shopify_service,
    analytics=analytics,
    insights=insights,
    report_generator=report_generator,
    email_service=email_service
)

@app.route('/')
def index():
    """Main page for Shopify Weekly Summary"""
    # Get recent feedback
    recent_feedback = feedback_db.get_recent_feedback(limit=10)
    
    # Get the current week's dates
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    return render_template('index.html',
                         recent_feedback=recent_feedback,
                         current_week_start=start_of_week.strftime('%Y-%m-%d'),
                         current_week_end=end_of_week.strftime('%Y-%m-%d'))

@app.route('/generate-report', methods=['POST'])
def generate_report():
    """Generate and send weekly report"""
    try:
        data = request.json
        recipient_email = data.get('email')
        recipient_name = data.get('name', 'there')
        week_start = data.get('week_start')
        week_end = data.get('week_end')
        
        # Convert dates
        start_date = datetime.strptime(week_start, '%Y-%m-%d')
        end_date = datetime.strptime(week_end, '%Y-%m-%d')
        
        # Generate report
        weekly_data = analytics.get_weekly_summary(start_date, end_date)
        conversational_report = insights.generate_weekly_insights(
            weekly_data, 
            recipient_name,
            feedback_db
        )
        
        # Generate PDF
        pdf_path = report_generator.generate_pdf_report(
            weekly_data,
            conversational_report,
            start_date,
            end_date
        )
        
        # Send email
        email_service.send_weekly_report(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            weekly_data=weekly_data,
            conversational_report=conversational_report,
            pdf_path=pdf_path
        )
        
        return jsonify({'success': True, 'message': 'Report sent successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/send-test-email', methods=['POST'])
def send_test_email():
    """Send a test email"""
    try:
        data = request.json
        recipient_email = data.get('email')
        
        # Send test email
        email_service.send_test_email(recipient_email)
        
        return jsonify({'success': True, 'message': 'Test email sent!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/process-replies', methods=['POST'])
def process_replies():
    """Manually trigger reply processing"""
    try:
        count = reply_processor.process_new_replies()
        return jsonify({
            'success': True, 
            'message': f'Processed {count} new replies'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Start the scheduler
    scheduler.start()
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)