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
            "Hope you had a fantastic weekend!",
            "Trust your week is off to a great start!",
            "Hope this Monday finds you well!",
            "Another week, another opportunity to shine!",
        ]
        return random.choice(openings)
    
    def get_closing(self):
        closings = [
            "Looking forward to hearing your thoughts!",
            "Can't wait to hear what you think!",
            "Would love to hear your perspective on this!",
            "Excited to hear your insights!",
        ]
        return random.choice(closings)
    
    def get_sign_off(self):
        sign_offs = [
            "Cheers",
            "Best",
            "Warmly",
            "Talk soon",
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
            <p>{self.get_opening_line()} I've been digging through your numbers from last week, and I've got some interesting insights to share.</p>
            
            <h2>🌟 Your Week in Highlights</h2>
            <div class="highlight-box">
                <div class="metric">
                    <div class="metric-value">${analytics_data['total_revenue']:,.2f}</div>
                    <div class="metric-label">Total Revenue</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{analytics_data['total_orders']}</div>
                    <div class="metric-label">Orders</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${analytics_data['avg_order_value']:.2f}</div>
                    <div class="metric-label">Avg Order Value</div>
                </div>
            </div>
            
            <h2>💡 What Caught My Eye</h2>
            {insights}
            
            <h2>🤔 I'm Curious About...</h2>
            {"".join([f'<div class="question">{q}</div>' for q in questions])}
            
            <p style="margin-top: 30px;">{self.get_closing()} Just hit reply - I actually read these. 😊</p>
            
            <p>{self.get_sign_off()},<br>
            Your Friendly Analytics Assistant</p>
            
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

{self.get_opening_line()} I've been digging through your numbers from last week, and I've got some interesting insights to share.

YOUR WEEK IN HIGHLIGHTS
=======================
Total Revenue: ${analytics_data['total_revenue']:,.2f}
Orders: {analytics_data['total_orders']}
Average Order Value: ${analytics_data['avg_order_value']:.2f}

WHAT CAUGHT MY EYE
==================
{insights}

I'M CURIOUS ABOUT...
===================
{chr(10).join([f'- {q}' for q in questions])}

{self.get_closing()} Just hit reply - I actually read these. :)

{self.get_sign_off()},
Your Friendly Analytics Assistant

P.S. Full report attached if you want all the nerdy details!

View Full Dashboard: {os.getenv('APP_URL', 'http://localhost:5000')}/shopify-summary
        """
        return text
    
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