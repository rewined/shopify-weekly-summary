import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import imapclient
import email
from email.header import decode_header
from email_reply_parser import EmailReplyParser
from .feedback_database import FeedbackDatabase
from .conversational_insights import ConversationalInsights
from .email_responder import EmailResponder


class ReplyProcessor:
    def __init__(self):
        self.db = FeedbackDatabase()
        self.insights = ConversationalInsights()
        self.responder = EmailResponder()
        
        # IMAP configuration
        self.imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        self.username = os.getenv('IMAP_USERNAME')
        self.password = os.getenv('IMAP_PASSWORD')
        
        if not all([self.username, self.password]):
            raise ValueError("Missing IMAP configuration. Please check environment variables.")
    
    def process_replies(self) -> List[Dict]:
        """Check for and process new email replies"""
        processed_replies = []
        
        try:
            # Connect to IMAP server
            client = imapclient.IMAPClient(self.imap_server, port=self.imap_port, ssl=True)
            client.login(self.username, self.password)
            
            # Select inbox
            client.select_folder('INBOX')
            
            # Search for unread emails with our subject pattern
            messages = client.search(['UNSEEN', 'SUBJECT', 'Candlefish'])
            
            for msg_id in messages:
                try:
                    # Fetch the email
                    raw_message = client.fetch([msg_id], ['RFC822'])[msg_id][b'RFC822']
                    email_message = email.message_from_bytes(raw_message)
                    
                    # Process the email
                    processed = self._process_single_email(email_message)
                    if processed:
                        processed_replies.append(processed)
                        
                        # Mark as read
                        client.add_flags(msg_id, [imapclient.SEEN])
                
                except Exception as e:
                    print(f"Error processing email {msg_id}: {str(e)}")
                    continue
            
            client.logout()
            
        except Exception as e:
            print(f"Error connecting to IMAP server: {str(e)}")
        
        return processed_replies
    
    def _process_single_email(self, email_message) -> Dict:
        """Process a single email message"""
        # Extract email details
        sender = self._extract_email_address(email_message['From'])
        subject = self._decode_header(email_message['Subject'])
        date_received = email_message['Date']
        
        # Extract reply content
        body = self._extract_reply_text(email_message)
        
        # Parse out just the reply (remove quoted text)
        reply_text = EmailReplyParser.parse_reply(body)
        
        # Extract sender name
        sender_name = self._extract_sender_name(email_message['From'])
        
        # Try to determine which report this is replying to
        report_date = self._extract_report_date(subject, body)
        
        # Save to database
        feedback_id = self.db.add_feedback(
            email=sender,
            content=reply_text,
            subject=subject,
            name=sender_name,
            report_date=report_date
        )
        
        # Process with AI to extract context
        context = self.insights.process_feedback(reply_text, sender)
        
        # Mark as processed with context
        self.db.mark_feedback_processed(feedback_id, context)
        
        # NEW: Generate and send Sophie's response
        try:
            response_sent = self.responder.process_and_respond(
                sender_email=sender,
                sender_name=sender_name,
                original_message=reply_text,
                subject=subject
            )
            
            if response_sent:
                print(f"Sophie's response sent successfully to {sender}")
                # Log the response in the database
                self.db.add_feedback(
                    email=sender,
                    content=f"[Sophie's automated response sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
                    subject=f"Re: {subject}",
                    name="Sophie Blake",
                    report_date=report_date
                )
            else:
                print(f"Failed to send Sophie's response to {sender}")
                
        except Exception as e:
            print(f"Error generating/sending Sophie's response: {str(e)}")
        
        return {
            'id': feedback_id,
            'sender': sender,
            'name': sender_name,
            'subject': subject,
            'content': reply_text,
            'context': context,
            'received_at': date_received,
            'response_sent': response_sent if 'response_sent' in locals() else False
        }
    
    def _extract_email_address(self, from_header: str) -> str:
        """Extract email address from From header"""
        match = re.search(r'<(.+?)>', from_header)
        if match:
            return match.group(1)
        
        # If no angle brackets, assume the whole thing is the email
        return from_header.strip()
    
    def _extract_sender_name(self, from_header: str) -> str:
        """Extract sender name from From header"""
        match = re.match(r'^(.+?)\s*<', from_header)
        if match:
            name = match.group(1).strip()
            # Remove quotes if present
            name = name.strip('"\'')
            return name
        
        # If no name found, use part before @ in email
        email_addr = self._extract_email_address(from_header)
        return email_addr.split('@')[0]
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header value"""
        if not header_value:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(header_value):
            if isinstance(part, bytes):
                if encoding:
                    decoded_parts.append(part.decode(encoding))
                else:
                    decoded_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                decoded_parts.append(part)
        
        return ' '.join(decoded_parts)
    
    def _extract_reply_text(self, email_message) -> str:
        """Extract plain text content from email"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    body = part.get_payload(decode=True).decode(charset, errors='ignore')
                    break
        else:
            charset = email_message.get_content_charset() or 'utf-8'
            body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
        
        return body
    
    def _extract_report_date(self, subject: str, body: str) -> str:
        """Try to extract the report date this email is replying to"""
        # Look for date patterns in subject
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        
        match = re.search(date_pattern, subject)
        if match:
            return match.group(1)
        
        # Look in body for "Week of" patterns
        week_pattern = r'Week of (\d{4}-\d{2}-\d{2})'
        match = re.search(week_pattern, body)
        if match:
            return match.group(1)
        
        # Default to current week's Monday
        today = datetime.now()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday)
        return last_monday.strftime('%Y-%m-%d')
    
    def update_preferences_from_feedback(self, email: str, context: Dict):
        """Update recipient preferences based on feedback context"""
        if not context.get('preferences'):
            return
        
        current_prefs = self.db.get_recipient_preferences(email)
        
        # Check for day preferences
        for day_name, day_num in [
            ('monday', 0), ('tuesday', 1), ('wednesday', 2),
            ('thursday', 3), ('friday', 4), ('saturday', 5), ('sunday', 6)
        ]:
            if day_name in context['preferences'].get('text', '').lower():
                current_prefs['preferred_day'] = day_num
                break
        
        # Check for time preferences
        time_match = re.search(r'(\d{1,2})\s*(am|pm)', 
                              context['preferences'].get('text', ''), re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            if time_match.group(2).lower() == 'pm' and hour != 12:
                hour += 12
            elif time_match.group(2).lower() == 'am' and hour == 12:
                hour = 0
            current_prefs['preferred_hour'] = hour
        
        # Update tracking items
        if context.get('track_items'):
            current_tracking = current_prefs.get('custom_tracking', [])
            if isinstance(current_tracking, str):
                current_tracking = json.loads(current_tracking) if current_tracking else []
            
            current_tracking.extend(context['track_items'])
            current_prefs['custom_tracking'] = list(set(current_tracking))
        
        self.db.update_recipient_preferences(email, current_prefs)