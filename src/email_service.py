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
    
    
    def _removed_create_weekly_email_html(self, recipient_name, analytics_data, insights, questions):
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
            
            {self._format_goals_performance(analytics_data)}
            
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
        # Check if Sophie provided a complete email
        insights_text = insights if isinstance(insights, str) else insights.get('insights_text', '')
        
        # If the insights already contain a complete email (starts with a greeting), use it as-is
        if insights_text and any(insights_text.lower().startswith(greeting) for greeting in ['hi ', 'hey ', 'hello ', 'good morning', 'good afternoon', 'morning']):
            # Just add the P.S. about the attachment if it's not already there
            if 'attached' not in insights_text.lower():
                insights_text += "\n\nP.S. I attached the full report with all the details."
            return insights_text
        
        # Otherwise, use the fallback template (this should rarely happen with the new prompt)
        goals_text = ""
        if 'goals' in analytics_data and 'conversion_metrics' in analytics_data:
            charleston_metrics = analytics_data['conversion_metrics'].get('charleston', {})
            charleston_current = analytics_data['current_week_by_location'].get('charleston', {})
            charleston_goals = analytics_data['goals'].get('charleston', {})
            
            boston_metrics = analytics_data['conversion_metrics'].get('boston', {})
            boston_current = analytics_data['current_week_by_location'].get('boston', {})
            boston_goals = analytics_data['goals'].get('boston', {})
            
            goals_text = "\n\nQuick check on our goals:\n\n"
            
            if charleston_current.get('order_count', 0) > 0:
                revenue_pct = charleston_metrics.get('revenue_vs_goal_pct', 0)
                avg_ticket = charleston_current.get('avg_order_value', 0)
                avg_goal = charleston_goals.get('avg_ticket_goal', 0)
                goals_text += f"Charleston hit {revenue_pct:.0f}% of revenue goal with ${avg_ticket:.0f} average tickets (goal is ${avg_goal:.0f})\n"
            
            if boston_current.get('order_count', 0) > 0:
                revenue_pct = boston_metrics.get('revenue_vs_goal_pct', 0)
                avg_ticket = boston_current.get('avg_order_value', 0)
                goals_text += f"Boston hit {revenue_pct:.0f}% of target with ${avg_ticket:.0f} average tickets\n"
        
        # Fallback template
        text = f"""Hi {recipient_name},

Hope your week is off to a good start. I just finished going through last week's numbers and wanted to share what I found.

You brought in ${analytics_data['total_revenue']:,.2f} from {analytics_data['total_orders']} orders, with customers spending about ${analytics_data['avg_order_value']:.2f} on average.{goals_text}

{insights_text}

{chr(10).join([f'- {q}' for q in questions])}

Let me know if you have any questions or if there's anything specific you'd like me to look into next week.

Thanks,
Sophie Blake
Rewined Intern

P.S. I attached the full report with all the details."""
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
    
    def _format_goals_performance(self, analytics_data):
        """Format performance vs goals section"""
        if 'goals' not in analytics_data or 'conversion_metrics' not in analytics_data:
            return ""
        
        goals = analytics_data['goals']
        metrics = analytics_data['conversion_metrics']
        
        section = """
        <h2>🎯 How We're Doing vs Goals</h2>
        <div style="font-size: 16px; line-height: 1.6; margin: 20px 0;">
        """
        
        # Charleston performance
        charleston_metrics = metrics.get('charleston', {})
        charleston_goals = goals.get('charleston', {})
        charleston_current = analytics_data['current_week_by_location'].get('charleston', {})
        
        if charleston_current.get('order_count', 0) > 0:
            section += f"""
            <p><strong style="color: #667eea;">Charleston:</strong> """
            
            # Revenue vs goal
            revenue_pct = charleston_metrics.get('revenue_vs_goal_pct', 0)
            if revenue_pct >= 100:
                section += f"Crushed it! Hit <strong>{revenue_pct:.0f}%</strong> of the revenue goal "
            elif revenue_pct >= 90:
                section += f"So close! Hit <strong>{revenue_pct:.0f}%</strong> of the revenue goal "
            else:
                section += f"Hit <strong>{revenue_pct:.0f}%</strong> of the revenue goal "
            
            # Average ticket vs goal
            avg_ticket_pct = charleston_metrics.get('avg_ticket_vs_goal_pct', 0)
            avg_ticket_actual = charleston_current.get('avg_order_value', 0)
            avg_ticket_goal = charleston_goals.get('avg_ticket_goal', 0)
            
            if avg_ticket_actual >= avg_ticket_goal:
                section += f"and average tickets are looking great at <strong>${avg_ticket_actual:.0f}</strong> (goal was ${avg_ticket_goal:.0f})!"
            else:
                section += f"but average tickets are a bit low at <strong>${avg_ticket_actual:.0f}</strong> (goal is ${avg_ticket_goal:.0f})."
            
            section += "</p>"
        
        # Boston performance
        boston_metrics = metrics.get('boston', {})
        boston_goals = goals.get('boston', {})
        boston_current = analytics_data['current_week_by_location'].get('boston', {})
        
        if boston_current.get('order_count', 0) > 0:
            section += f"""
            <p><strong style="color: #d53f8c;">Boston:</strong> """
            
            revenue_pct = boston_metrics.get('revenue_vs_goal_pct', 0)
            if revenue_pct >= 100:
                section += f"Killing it for a new store! Hit <strong>{revenue_pct:.0f}%</strong> of target "
            else:
                section += f"Building momentum - hit <strong>{revenue_pct:.0f}%</strong> of target "
            
            avg_ticket_actual = boston_current.get('avg_order_value', 0)
            avg_ticket_goal = boston_goals.get('avg_ticket_goal', 0)
            
            section += f"with ${avg_ticket_actual:.0f} average tickets."
            section += "</p>"
        
        section += "</div>"
        return section
    
    def send_weekly_report(self, recipient_email, recipient_name, analytics_data, insights, questions, pdf_attachment=None):
        try:
            subject_lines = [
                f"Weekly numbers for {analytics_data['week_start']}",
                f"Candlefish weekly recap - {analytics_data['week_start']}",
                f"Your weekly report is ready",
            ]
            
            msg = Message(
                subject=random.choice(subject_lines),
                sender=os.getenv('MAIL_DEFAULT_SENDER'),
                recipients=[recipient_email],
                reply_to=os.getenv('MAIL_USERNAME')
            )
            
            # Only use plain text, no HTML
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
                subject="Candlefish Weekly Report Error",
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
                subject="Test - Candlefish Weekly Analytics",
                sender=os.getenv('MAIL_DEFAULT_SENDER'),
                recipients=[recipient_email],
                reply_to=os.getenv('MAIL_USERNAME')
            )
            
            msg.body = """Hi,

This is a test email to confirm your weekly analytics reports are set up correctly.

Starting next Monday, you'll receive:
- Weekly performance metrics for Charleston and Boston stores
- Progress toward revenue and average ticket goals
- Top selling products by location
- Analysis and insights about store performance

You can reply to these emails with any questions or feedback.

Thanks,
Sophie Blake
Rewined Intern
            """
            
            self.mail.send(msg)
            return True
            
        except Exception as e:
            print(f"Error sending test email: {str(e)}")
            raise