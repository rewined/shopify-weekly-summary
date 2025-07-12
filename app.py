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
from src.scheduler import ShopifyScheduler
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'shopify-weekly-summary-secret-2024')

# Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))

# Initialize services with lazy loading
shopify_service = None
analytics = None
insights = None
report_generator = None
email_service = None
feedback_db = None
reply_processor = None
scheduler = None

def init_services():
    global shopify_service, analytics, insights, report_generator, email_service, feedback_db, reply_processor, scheduler
    
    shopify_service = ShopifyService()
    analytics = ShopifyAnalytics(shopify_service)
    insights = ConversationalInsights()
    report_generator = ShopifyReportGenerator()
    email_service = ConversationalEmailService(app)
    feedback_db = FeedbackDatabase()
    reply_processor = ReplyProcessor()
    scheduler = ShopifyScheduler(app)

@app.route('/')
def index():
    """Main page for Shopify Weekly Summary"""
    if not feedback_db:
        init_services()
    
    # For now, we'll set recent_feedback to empty list
    # TODO: Implement get_recent_feedback method if needed
    recent_feedback = []
    
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
    if not shopify_service:
        init_services()
    
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
        weekly_data = analytics.analyze_weekly_data(start_date)
        # Get feedback context for recipient
        feedback_context = feedback_db.get_feedback_context_for_email(recipient_email)
        
        conversational_report = insights.generate_insights(
            weekly_data, 
            recipient_name,
            feedback_context
        )
        
        # Generate PDF
        pdf_path = report_generator.generate_report(
            weekly_data,
            conversational_report.get('insights_html', '')
        )
        
        # Send email
        email_service.send_weekly_report(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            analytics_data=weekly_data,
            insights=conversational_report.get('insights_html', ''),
            questions=conversational_report.get('questions', []),
            pdf_attachment=pdf_path
        )
        
        return jsonify({'success': True, 'message': 'Report sent successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/send-test-email', methods=['POST'])
def send_test_email():
    """Send a test email"""
    if not email_service:
        init_services()
    
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
    if not reply_processor:
        init_services()
    
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
    # Initialize services
    init_services()
    
    # Start the scheduler
    scheduler.start()
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)