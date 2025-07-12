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
            conversational_report.get('insights_text', conversational_report.get('insights_html', ''))
        )
        
        # Send email
        email_service.send_weekly_report(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            analytics_data=weekly_data,
            insights=conversational_report.get('insights_text', conversational_report.get('insights_html', '')),
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

@app.route('/test-shopify')
def test_shopify():
    """Test Shopify connection"""
    if not shopify_service:
        init_services()
    
    try:
        # Try to fetch recent orders
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # Look back 1 year instead of 30 days
        
        print(f"Testing Shopify connection for date range: {start_date} to {end_date}")
        orders = shopify_service.get_orders_for_period(start_date, end_date)
        
        # Also try to get a count of all orders
        try:
            import shopify
            order_count = shopify.Order.count()
            print(f"Total orders in store: {order_count}")
        except Exception as count_error:
            order_count = f"Error: {str(count_error)}"
        
        return jsonify({
            'success': True,
            'orders_found': len(orders),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'shop_domain': shopify_service.shop_domain,
            'total_orders_in_store': order_count,
            'api_permissions': 'Check Railway logs for details'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'shop_domain': shopify_service.shop_domain if shopify_service else 'Not initialized'
        }), 500

@app.route('/analyze-locations')
def analyze_locations():
    """Analyze Shopify locations to identify Charleston and Boston"""
    if not shopify_service:
        init_services()
    
    try:
        # Get orders from different time periods
        # Pre-Boston (before July 2024)
        pre_boston_end = datetime(2024, 6, 30)
        pre_boston_start = datetime(2024, 6, 1)
        
        # Post-Boston (after July 2024)
        post_boston_start = datetime(2024, 8, 1)
        post_boston_end = datetime(2024, 8, 31)
        
        # Recent
        recent_end = datetime.now()
        recent_start = recent_end - timedelta(days=7)
        
        print("Fetching orders from different periods...")
        pre_boston_orders = shopify_service.get_orders_for_period(pre_boston_start, pre_boston_end)
        post_boston_orders = shopify_service.get_orders_for_period(post_boston_start, post_boston_end)
        recent_orders = shopify_service.get_orders_for_period(recent_start, recent_end)
        
        # Analyze location patterns
        def analyze_period_locations(orders, period_name):
            from collections import defaultdict
            location_stats = defaultdict(lambda: {'count': 0, 'pos_count': 0, 'revenue': 0})
            
            for order in orders:
                location_id = str(order.get('location_id', 'none'))
                source = order.get('source_name', '')
                
                location_stats[location_id]['count'] += 1
                location_stats[location_id]['revenue'] += order.get('total_price', 0)
                
                if source.lower() == 'pos':
                    location_stats[location_id]['pos_count'] += 1
            
            return {
                'period': period_name,
                'locations': dict(location_stats)
            }
        
        # Try to get location details
        location_details = []
        try:
            import shopify
            locations = shopify.Location.find()
            for loc in locations:
                location_details.append({
                    'id': str(loc.id),
                    'name': loc.name,
                    'city': getattr(loc, 'city', 'N/A'),
                    'province': getattr(loc, 'province', 'N/A'),
                    'active': getattr(loc, 'active', True)
                })
        except Exception as e:
            print(f"Could not fetch location details: {e}")
        
        return jsonify({
            'success': True,
            'location_details': location_details,
            'analysis': {
                'pre_boston': analyze_period_locations(pre_boston_orders, 'Pre-Boston (June 2024)'),
                'post_boston': analyze_period_locations(post_boston_orders, 'Post-Boston (Aug 2024)'),
                'recent': analyze_period_locations(recent_orders, 'Recent (Last 7 days)')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Initialize services
    init_services()
    
    # Start the scheduler
    scheduler.start()
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)