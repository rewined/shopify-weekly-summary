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
        
        print(f"Generating report for {recipient_email} from {week_start} to {week_end}")
        
        # Convert dates
        start_date = datetime.strptime(week_start, '%Y-%m-%d')
        end_date = datetime.strptime(week_end, '%Y-%m-%d')
        
        # Generate report (disable trends for now to prevent timeouts)
        print("Fetching analytics data...")
        try:
            weekly_data = analytics.analyze_weekly_data(start_date, include_trends=False)
        except Exception as e:
            print(f"Error fetching analytics: {str(e)}")
            return jsonify({'success': False, 'error': f'Failed to fetch analytics data: {str(e)}'}), 500
            
        # Get feedback context for recipient
        feedback_context = feedback_db.get_feedback_context_for_email(recipient_email)
        
        print("Generating AI insights...")
        try:
            conversational_report = insights.generate_insights(
                weekly_data, 
                recipient_name,
                feedback_context
            )
        except Exception as e:
            print(f"Error generating insights: {str(e)}")
            # Use fallback insights if AI generation fails
            conversational_report = {
                'insights_text': 'Unable to generate AI insights at this time.',
                'questions': []
            }
        
        # Skip PDF generation to avoid timeouts
        pdf_path = None
        
        print("Sending email...")
        insights_content = conversational_report.get('insights_text', conversational_report.get('full_email', ''))
        
        # Send email
        email_service.send_weekly_report(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            analytics_data=weekly_data,
            insights=insights_content,
            questions=conversational_report.get('questions', []),
            pdf_attachment=pdf_path
        )
        
        print("Report sent successfully!")
        return jsonify({'success': True, 'message': 'Report sent successfully!'})
        
    except Exception as e:
        print(f"Error in generate_report: {str(e)}")
        import traceback
        traceback.print_exc()
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

@app.route('/test-analytics')
def test_analytics():
    """Test analytics without sending email"""
    if not shopify_service:
        init_services()
    
    try:
        # Get last week's data
        today = datetime.now()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday + 7)
        
        # Get basic analytics without trends
        print("Testing analytics fetch...")
        weekly_data = analytics.analyze_weekly_data(week_start, include_trends=False)
        
        # Extract key metrics
        summary = {
            'success': True,
            'week': weekly_data['week_start'],
            'total_revenue': weekly_data['total_revenue'],
            'total_orders': weekly_data['total_orders'],
            'charleston_orders': weekly_data['current_week_by_location']['charleston']['order_count'],
            'boston_orders': weekly_data['current_week_by_location']['boston']['order_count'],
            'product_categories': {
                cat: {'revenue': data['revenue'], 'items': data['count']}
                for cat, data in weekly_data.get('product_categories', {}).items()
            } if 'product_categories' in weekly_data else None
        }
        
        return jsonify(summary)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

@app.route('/test-quick-report')
def test_quick_report():
    """Quick test without AI or PDF generation"""
    if not shopify_service:
        init_services()
    
    try:
        # Get last week's data
        today = datetime.now()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday + 7)
        
        print("Testing quick analytics fetch...")
        weekly_data = analytics.analyze_weekly_data(week_start, include_trends=False)
        
        # Create a simple text summary without AI
        summary = f"""
Weekly Summary for {weekly_data['week_start']} to {weekly_data['week_end']}

Total Revenue: ${weekly_data['total_revenue']:,.2f}
Total Orders: {weekly_data['total_orders']}
Average Order Value: ${weekly_data['avg_order_value']:.2f}

Charleston:
- Orders: {weekly_data['current_week_by_location']['charleston']['order_count']}
- Revenue: ${weekly_data['current_week_by_location']['charleston']['total_revenue']:,.2f}

Boston:
- Orders: {weekly_data['current_week_by_location']['boston']['order_count']}
- Revenue: ${weekly_data['current_week_by_location']['boston']['total_revenue']:,.2f}
        """
        
        return f"<pre>{summary}</pre>"
        
    except Exception as e:
        import traceback
        return f"<pre>Error: {str(e)}\n\n{traceback.format_exc()}</pre>", 500

@app.route('/test-email-generation')
def test_email_generation():
    """Test the email generation process"""
    if not insights:
        init_services()
    
    try:
        # Create sample analytics data
        sample_data = {
            'week_start': '2024-12-30',
            'week_end': '2025-01-05',
            'total_revenue': 13406.50,
            'total_orders': 250,
            'avg_order_value': 53.63,
            'current_week_by_location': {
                'charleston': {'order_count': 150, 'total_revenue': 7000, 'avg_order_value': 46.67},
                'boston': {'order_count': 100, 'total_revenue': 6406.50, 'avg_order_value': 64.07}
            },
            'goals': {
                'charleston': {'revenue_goal': 25000, 'avg_ticket_goal': 89},
                'boston': {'revenue_goal': 100000, 'avg_ticket_goal': 75}
            },
            'conversion_metrics': {
                'charleston': {'revenue_vs_goal_pct': 32, 'avg_ticket_vs_goal_pct': 52},
                'boston': {'revenue_vs_goal_pct': 6, 'avg_ticket_vs_goal_pct': 85}
            }
        }
        
        # Generate insights
        result = insights.generate_insights(sample_data, 'Adam', {})
        
        # Create detailed debug output
        debug_output = {
            'raw_result_keys': list(result.keys()),
            'has_insights_text': 'insights_text' in result,
            'has_full_email': 'full_email' in result,
            'insights_text_preview': result.get('insights_text', '')[:200] if 'insights_text' in result else None,
            'full_email_preview': result.get('full_email', '')[:200] if 'full_email' in result else None,
            'questions': result.get('questions', []),
            'result_type': type(result).__name__
        }
        
        # Also show what the email service would receive
        insights_content = result.get('insights_text', result.get('full_email', ''))
        debug_output['email_content_preview'] = insights_content[:500] if insights_content else None
        debug_output['email_starts_with_json'] = insights_content.strip().startswith('{') if insights_content else False
        
        return jsonify(debug_output)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/test-json-email')
def test_json_email():
    """Test JSON email extraction"""
    test_json = '''
    {
      "full_email": "Hey Adam,\\n\\nHow's it going? I've been digging into this week's numbers and wanted to share some quick thoughts.\\n\\nBest,\\nSophie",
      "questions": ["Question 1", "Question 2"]
    }
    '''
    
    # Test the email service
    if not email_service:
        init_services()
    
    result = email_service.create_weekly_email_text(
        'Adam',
        {'total_revenue': 1000, 'total_orders': 10, 'avg_order_value': 100},
        test_json.strip(),
        []
    )
    
    return f"<pre>Input JSON:\n{test_json}\n\nExtracted Email:\n{result}</pre>"

@app.route('/test-google-sheets')
def test_google_sheets():
    """Test Google Sheets connection via MCP"""
    if not analytics:
        init_services()
    
    try:
        # Test the connection
        connection_test = analytics.sheets_service.test_connection()
        
        # Try to get sample goals
        from datetime import datetime
        sample_goals = analytics.sheets_service.get_weekly_goals(datetime.now())
        
        return jsonify({
            'connection_test': connection_test,
            'sample_goals': sample_goals,
            'spreadsheet_ids': {
                'charleston': analytics.sheets_service.charleston_sheet_id,
                'boston': analytics.sheets_service.boston_sheet_id
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

if __name__ == '__main__':
    # Initialize services
    init_services()
    
    # Start the scheduler
    scheduler.start()
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)