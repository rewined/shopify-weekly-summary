import os
from datetime import datetime
from flask_mail import Mail, Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import random


class ConversationalEmailService:
    def __init__(self, app=None):
        self.mail = None
        self.app = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        self.mail = Mail(app)
    
    def get_greeting(self):
        greetings = [
            "Hey {name}! 👋",
            "Hi {name}!",
            "Hello {name}!",
            "Good morning {name}!",
        ]
        return random.choice(greetings)
    
    def get_opening_line(self):
        openings = [
            "Hope you had an awesome weekend!",
            "Happy Monday!",
            "Hope your week's starting off great!",
            "Another week, another batch of data to dig through!",
            "Hope you're ready for some numbers!",
        ]
        return random.choice(openings)
    
    def get_closing(self):
        closings = [
            "Let me know what you think!",
            "Can't wait to hear back from you!",
            "Would love to know if I'm on the right track here!",
            "Super curious to hear your thoughts!",
            "Hit me back with any questions!",
        ]
        return random.choice(closings)
    
    def get_sign_off(self):
        sign_offs = [
            "Cheers",
            "Best",
            "Thanks",
            "Talk soon",
            "-Sophie",
        ]
        return random.choice(sign_offs)
    
    def create_weekly_email_html(self, recipient_name, analytics_data, insights, questions):
        template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }}
                .highlight-box {{
                    background: #f7fafc;
                    border-left: 4px solid #667eea;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .metric {{
                    display: inline-block;
                    margin: 10px 20px 10px 0;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #667eea;
                }}
                .metric-label {{
                    font-size: 14px;
                    color: #718096;
                }}
                .question {{
                    background: #fef5e7;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 10px 0;
                }}
                .cta {{
                    background: #667eea;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                    font-size: 14px;
                    color: #718096;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0;">Your Candlefish Weekly Recap 🕯️</h1>
                <p style="margin: 10px 0 0 0;">Week of {analytics_data['week_start']} - {analytics_data['week_end']}</p>
            </div>
            
            <p>{self.get_greeting().format(name=recipient_name)}</p>
            <p>{self.get_opening_line()} So I just finished crunching through last week's numbers and found some pretty interesting stuff I think you'll want to see!</p>
            
            <h2>🌟 Here's What Happened This Week</h2>
            <div class="highlight-box" style="font-size: 16px; line-height: 1.6;">
                <p style="margin: 0;">You guys brought in <strong style="color: #667eea; font-size: 24px;">${analytics_data['total_revenue']:,.2f}</strong> this week! 
                That came from <strong>{analytics_data['total_orders']}</strong> happy customers, 
                with each one spending about <strong>${analytics_data['avg_order_value']:.2f}</strong> on average.</p>
            </div>
            
            {self._format_top_products_section(analytics_data)}
            
            <h2>💡 What Caught My Eye</h2>
            {insights}
            
            <h2>🤔 I'm Curious About...</h2>
            {"".join([f'<div class="question">{q}</div>' for q in questions])}
            
            <p style="margin-top: 30px;">{self.get_closing()} Just hit reply - I actually read these. 😊</p>
            
            <p>{self.get_sign_off()},<br>
            Sophie Blake<br>
            <span style="font-size: 12px; color: #718096;">Rewined Intern</span></p>
            
            <a href="{os.getenv('APP_URL', 'http://localhost:5000')}/shopify-summary" class="cta">View Full Dashboard</a>
            
            <div class="footer">
                <p>P.S. Full report attached if you want all the nerdy details!</p>
                <p style="font-size: 12px;">You're receiving this because you're subscribed to Candlefish weekly analytics. 
                <a href="mailto:{os.getenv('MAIL_USERNAME')}?subject=Unsubscribe">Unsubscribe</a></p>
            </div>
        </body>
        </html>
        """
        return template
    
    def create_weekly_email_text(self, recipient_name, analytics_data, insights, questions):
        text = f"""
{self.get_greeting().format(name=recipient_name)}

{self.get_opening_line()} So I just finished crunching through last week's numbers and found some pretty interesting stuff I think you'll want to see!

HERE'S WHAT HAPPENED THIS WEEK
==============================
You guys brought in ${analytics_data['total_revenue']:,.2f} this week! That came from {analytics_data['total_orders']} happy customers, 
with each one spending about ${analytics_data['avg_order_value']:.2f} on average.

WHAT CAUGHT MY EYE
==================
{insights}

I'M CURIOUS ABOUT...
===================
{chr(10).join([f'- {q}' for q in questions])}

{self.get_closing()} Just hit reply - I actually read these. :)

{self.get_sign_off()},
Sophie Blake
Rewined Intern

P.S. Full report attached if you want all the nerdy details!

View Full Dashboard: {os.getenv('APP_URL', 'http://localhost:5000')}/shopify-summary
        """
        return text
    
    def _format_top_products_section(self, analytics_data):
        """Format top products by location for email"""
        if 'product_performance_by_location' not in analytics_data:
            return ""
        
        charleston_products = analytics_data['product_performance_by_location']['charleston'][:3]
        boston_products = analytics_data['product_performance_by_location']['boston'][:3]
        
        if not charleston_products and not boston_products:
            return ""
        
        section = """
        <h2>🏆 What's Flying Off the Shelves</h2>
        <div style="font-size: 16px; line-height: 1.6; margin: 20px 0;">
        """
        
        if charleston_products:
            section += f"""
            <p><strong style="color: #667eea;">In Charleston:</strong> Your customers are loving 
            <strong>{charleston_products[0]['product'][:40]}{'...' if len(charleston_products[0]['product']) > 40 else ''}</strong> 
            (sold {charleston_products[0]['quantity_sold']} for ${charleston_products[0]['revenue']:,.0f})"""
            
            if len(charleston_products) > 1:
                section += f""", followed by <strong>{charleston_products[1]['product'][:30]}{'...' if len(charleston_products[1]['product']) > 30 else ''}</strong>"""
            
            section += ".</p>"
        
        if boston_products:
            section += f"""
            <p><strong style="color: #d53f8c;">In Boston:</strong> The top pick is 
            <strong>{boston_products[0]['product'][:40]}{'...' if len(boston_products[0]['product']) > 40 else ''}</strong> 
            (moved {boston_products[0]['quantity_sold']} units for ${boston_products[0]['revenue']:,.0f})"""
            
            if len(boston_products) > 1:
                section += f""", with <strong>{boston_products[1]['product'][:30]}{'...' if len(boston_products[1]['product']) > 30 else ''}</strong> coming in second"""
            
            section += ".</p>"
        elif analytics_data.get('current_week_by_location', {}).get('boston', {}).get('order_count', 0) == 0:
            section += '<p><strong style="color: #d53f8c;">Boston:</strong> Still warming up - no sales data this week.</p>'
        
        section += "</div>"
        
        return section
    
    def send_weekly_report(self, recipient_email, recipient_name, analytics_data, insights, questions, pdf_attachment=None):
        try:
            subject_lines = [
                f"Hey {recipient_name}! Your Candlefish weekly recap is here 🕯️",
                f"{recipient_name}, your weekly wins at Candlefish! 📊",
                f"Your Candlefish numbers are looking interesting, {recipient_name}! 👀",
            ]
            
            msg = Message(
                subject=random.choice(subject_lines),
                sender=os.getenv('MAIL_DEFAULT_SENDER'),
                recipients=[recipient_email],
                reply_to=os.getenv('MAIL_USERNAME')
            )
            
            msg.html = self.create_weekly_email_html(recipient_name, analytics_data, insights, questions)
            msg.body = self.create_weekly_email_text(recipient_name, analytics_data, insights, questions)
            
            if pdf_attachment:
                with open(pdf_attachment, 'rb') as f:
                    msg.attach(
                        f"candlefish_weekly_report_{analytics_data['week_start']}.pdf",
                        'application/pdf',
                        f.read()
                    )
            
            self.mail.send(msg)
            return True
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    def send_error_notification(self, error_message):
        try:
            msg = Message(
                subject="⚠️ Candlefish Weekly Report Error",
                sender=os.getenv('MAIL_DEFAULT_SENDER'),
                recipients=[os.getenv('MAIL_USERNAME')]
            )
            
            msg.body = f"""
Hi Admin,

There was an error generating the weekly Candlefish report:

{error_message}

Please check the logs and resolve the issue.

Best,
Analytics System
            """
            
            self.mail.send(msg)
            
        except Exception as e:
            print(f"Error sending error notification: {str(e)}")
    
    def send_test_email(self, recipient_email: str):
        """Send a test email to verify configuration"""
        try:
            msg = Message(
                subject="🎉 Sophie Blake here - Your Shopify Analytics are ready!",
                sender=os.getenv('MAIL_DEFAULT_SENDER'),
                recipients=[recipient_email],
                reply_to=os.getenv('MAIL_USERNAME')
            )
            
            msg.html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        border-radius: 10px;
                        margin-bottom: 30px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1 style="margin: 0;">Test Email from Sophie Blake 🕯️</h1>
                    <p style="margin: 10px 0 0 0;">Your Analytics Assistant</p>
                </div>
                
                <p>Hey there! 👋</p>
                
                <p>Great news - your email configuration is working perfectly! This is Sophie Blake, your friendly analytics assistant for Candlefish.</p>
                
                <p>When you receive your weekly reports, they'll include:</p>
                <ul>
                    <li>📊 Weekly sales performance and trends</li>
                    <li>🎯 Top-performing products</li>
                    <li>👥 Customer insights</li>
                    <li>📈 Year-over-year comparisons</li>
                    <li>💡 AI-powered insights and recommendations</li>
                </ul>
                
                <p>The best part? You can simply reply to my emails with any context, questions, or feedback, and I'll incorporate that into future reports!</p>
                
                <p>Looking forward to helping you understand your business better!</p>
                
                <p>Cheers,<br>
                Sophie Blake<br>
                <span style="font-size: 12px; color: #718096;">Your Friendly Analytics Assistant</span></p>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 14px; color: #718096;">
                    <p>P.S. You'll receive your weekly reports every Monday morning!</p>
                </div>
            </body>
            </html>
            """
            
            msg.body = """
Hey there! 👋

Great news - your email configuration is working perfectly! This is Sophie Blake, your friendly analytics assistant for Candlefish.

When you receive your weekly reports, they'll include:
- Weekly sales performance and trends
- Top-performing products
- Customer insights
- Year-over-year comparisons
- AI-powered insights and recommendations

The best part? You can simply reply to my emails with any context, questions, or feedback, and I'll incorporate that into future reports!

Looking forward to helping you understand your business better!

Cheers,
Sophie Blake
Your Friendly Analytics Assistant

P.S. You'll receive your weekly reports every Monday morning!
            """
            
            self.mail.send(msg)
            return True
            
        except Exception as e:
            print(f"Error sending test email: {str(e)}")
            raise