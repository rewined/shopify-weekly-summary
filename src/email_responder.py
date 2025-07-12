import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from .conversational_insights import ConversationalInsights
from .memory_service import MemoryService
from .shopify_analytics import ShopifyAnalytics
from .shopify_service import ShopifyService

logger = logging.getLogger(__name__)

class EmailResponder:
    """Service for Sophie to respond to emails intelligently"""
    
    def __init__(self):
        self.insights = ConversationalInsights()
        self.memory = MemoryService()
        
        # Email configuration
        self.smtp_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('MAIL_PORT', '587'))
        self.username = os.getenv('MAIL_USERNAME')
        self.password = os.getenv('MAIL_PASSWORD')
        self.from_email = os.getenv('MAIL_DEFAULT_SENDER', self.username)
    
    def generate_response(self, 
                         sender_email: str,
                         sender_name: str,
                         original_message: str,
                         subject: str) -> Dict[str, str]:
        """Generate an intelligent response to an email"""
        
        # Get conversation context
        context = self.memory.get_conversation_context(sender_email)
        
        # Check if they're asking for specific data
        needs_fresh_data = self._check_data_request(original_message)
        
        # Get fresh analytics if needed
        current_data = {}
        if needs_fresh_data:
            try:
                # Try to get Shopify data first
                shopify = ShopifyService()
                analytics = ShopifyAnalytics(shopify)
                current_data = analytics.analyze_weekly_data(include_trends=False)
                shopify.close_session()
                logger.info("Successfully fetched fresh Shopify analytics data")
            except Exception as e:
                logger.error(f"Could not fetch Shopify data: {e}")
                
                # Fall back to Google Sheets data only
                try:
                    from .google_sheets_service import GoogleSheetsService
                    from datetime import datetime
                    
                    sheets_service = GoogleSheetsService()
                    goals = sheets_service.get_weekly_goals(datetime.now())
                    
                    current_data = {
                        'data_source': 'Google Sheets only (Shopify unavailable)',
                        'goals': goals,
                        'note': 'This is goals data from spreadsheets. Full analytics requires Shopify connection.'
                    }
                    logger.info("Successfully fetched Google Sheets goals data as fallback")
                except Exception as sheets_error:
                    logger.error(f"Could not fetch Google Sheets data either: {sheets_error}")
                    current_data = {
                        'error': 'Unable to fetch current data',
                        'note': 'Both Shopify and Google Sheets connections failed'
                    }
        
        # Build prompt for Claude
        prompt = f"""You are Sophie Blake, the analytics intern for Candlefish. You received this email from {sender_name}:

ORIGINAL EMAIL:
{original_message}

CONVERSATION HISTORY:
Last email you sent: {context['past_emails'][0]['key_points'] if context['past_emails'] else 'No recent emails'}
Topics they care about: {', '.join(context['topics_discussed']) if context['topics_discussed'] else 'General performance'}

{"CURRENT DATA (if they asked for updates):" + str(current_data) if current_data else ""}

Write a natural, helpful response as Sophie. Guidelines:
- Be conversational and friendly like in your weekly emails
- IMPORTANT: If current data is provided above, use those EXACT numbers and facts
- If asking about Charleston or Boston specifically, reference the goals from Google Sheets
- If they ask for data you don't have, explain what you can provide and offer to get it
- Reference past conversations naturally
- Keep it concise - this is a reply, not a full report
- Sign off as Sophie
- NEVER make up or estimate numbers - only use real data provided above

Format as JSON with keys: "subject" and "body"
"""
        
        try:
            response = self.insights.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Parse response
            import json
            try:
                result = json.loads(content)
                return {
                    'subject': result.get('subject', f"Re: {subject}"),
                    'body': result.get('body', 'Thanks for your email! Let me look into that for you.')
                }
            except:
                # Fallback if JSON parsing fails
                return {
                    'subject': f"Re: {subject}",
                    'body': content
                }
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                'subject': f"Re: {subject}",
                'body': f"Hi {sender_name},\n\nThanks for your email! I'll look into your question and get back to you with more details.\n\nBest,\nSophie"
            }
    
    def _check_data_request(self, message: str) -> bool:
        """Check if the email is asking for current data"""
        data_keywords = [
            'how are we doing',
            'current numbers',
            'this week',
            'today',
            'update',
            'latest',
            'how much',
            'what are the numbers',
            'performance',
            'sales',
            'goal',
            'charleston',
            'boston',
            'monday',
            'revenue',
            'numbers'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in data_keywords)
    
    def send_response(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email response"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"Sophie Blake <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Response sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            return False
    
    def process_and_respond(self, 
                           sender_email: str,
                           sender_name: str,
                           original_message: str,
                           subject: str) -> bool:
        """Process an email and send a response"""
        
        # Generate response
        response = self.generate_response(
            sender_email=sender_email,
            sender_name=sender_name,
            original_message=original_message,
            subject=subject
        )
        
        # Send it
        success = self.send_response(
            to_email=sender_email,
            subject=response['subject'],
            body=response['body']
        )
        
        if success:
            # Save to memory
            self.memory.save_enhanced_conversation(
                recipient_email=sender_email,
                email_content=response['body'],
                analytics_data={'type': 'reply', 'original_subject': subject},
                questions=[],
                topics=['email_reply']
            )
        
        return success