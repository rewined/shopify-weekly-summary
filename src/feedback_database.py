import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Any
import json


class FeedbackDatabase:
    def __init__(self, db_path: str = None):
        if not db_path:
            db_path = os.getenv('DATABASE_PATH', 'data/feedback.db')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                name TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subject TEXT,
                content TEXT NOT NULL,
                processed BOOLEAN DEFAULT 0,
                context_extracted TEXT,
                reply_to_report_date TEXT
            )
        ''')
        
        # Create conversation history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_email TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                report_date TEXT,
                insights_sent TEXT,
                questions_asked TEXT,
                pdf_path TEXT
            )
        ''')
        
        # Create preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipient_preferences (
                email TEXT PRIMARY KEY,
                name TEXT,
                preferred_day INTEGER DEFAULT 0,
                preferred_hour INTEGER DEFAULT 8,
                timezone TEXT DEFAULT 'America/New_York',
                active BOOLEAN DEFAULT 1,
                custom_tracking TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_feedback(self, email: str, content: str, subject: str = None, 
                    name: str = None, report_date: str = None) -> int:
        """Add new feedback to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (email, name, subject, content, reply_to_report_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (email, name, subject, content, report_date))
        
        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return feedback_id
    
    def get_unprocessed_feedback(self) -> List[Dict]:
        """Get all unprocessed feedback"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM feedback WHERE processed = 0
            ORDER BY received_at ASC
        ''')
        
        feedback = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return feedback
    
    def mark_feedback_processed(self, feedback_id: int, context: Dict):
        """Mark feedback as processed and store extracted context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE feedback 
            SET processed = 1, context_extracted = ?
            WHERE id = ?
        ''', (json.dumps(context), feedback_id))
        
        conn.commit()
        conn.close()
    
    def get_feedback_context_for_email(self, email: str) -> Dict:
        """Get all processed feedback context for a specific email"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT context_extracted, received_at 
            FROM feedback 
            WHERE email = ? AND processed = 1 AND context_extracted IS NOT NULL
            ORDER BY received_at DESC
            LIMIT 10
        ''', (email,))
        
        combined_context = {
            'track_items': [],
            'business_context': [],
            'preferences': {},
            'questions': []
        }
        
        for row in cursor.fetchall():
            try:
                context = json.loads(row['context_extracted'])
                
                # Merge contexts
                if 'track_items' in context:
                    combined_context['track_items'].extend(context['track_items'])
                
                if 'context' in context:
                    combined_context['business_context'].append({
                        'date': row['received_at'],
                        'context': context['context']
                    })
                
                if 'preferences' in context:
                    combined_context['preferences'].update(context['preferences'])
                
                if 'questions' in context:
                    combined_context['questions'].extend(context['questions'])
                    
            except json.JSONDecodeError:
                continue
        
        # Remove duplicates from track_items
        combined_context['track_items'] = list(set(combined_context['track_items']))
        
        conn.close()
        return combined_context
    
    def save_conversation(self, recipient_email: str, report_date: str, 
                         insights: str, questions: List[str], pdf_path: str = None):
        """Save conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversation_history 
            (recipient_email, report_date, insights_sent, questions_asked, pdf_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (recipient_email, report_date, insights, json.dumps(questions), pdf_path))
        
        conn.commit()
        conn.close()
    
    def get_recipient_preferences(self, email: str) -> Dict:
        """Get recipient preferences"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM recipient_preferences WHERE email = ?
        ''', (email,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            prefs = dict(row)
            if prefs.get('custom_tracking'):
                prefs['custom_tracking'] = json.loads(prefs['custom_tracking'])
            return prefs
        
        return {
            'email': email,
            'preferred_day': 0,
            'preferred_hour': 8,
            'timezone': 'America/New_York',
            'active': True
        }
    
    def update_recipient_preferences(self, email: str, preferences: Dict):
        """Update recipient preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert custom_tracking to JSON if present
        if 'custom_tracking' in preferences and isinstance(preferences['custom_tracking'], (list, dict)):
            preferences['custom_tracking'] = json.dumps(preferences['custom_tracking'])
        
        # Build update query dynamically
        fields = []
        values = []
        for key, value in preferences.items():
            if key != 'email':
                fields.append(f"{key} = ?")
                values.append(value)
        
        values.append(email)
        
        cursor.execute(f'''
            INSERT OR REPLACE INTO recipient_preferences 
            (email, {', '.join(preferences.keys())})
            VALUES (?, {', '.join(['?' for _ in preferences.values()])})
        ''', [email] + list(preferences.values()))
        
        conn.commit()
        conn.close()
    
    def get_all_active_recipients(self) -> List[str]:
        """Get all active recipient emails"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First, get from preferences
        cursor.execute('''
            SELECT email FROM recipient_preferences WHERE active = 1
        ''')
        
        recipients = [row[0] for row in cursor.fetchall()]
        
        # If no preferences set, get from environment
        if not recipients:
            env_recipients = os.getenv('DEFAULT_RECIPIENTS', os.getenv('EMAIL_RECIPIENTS', 'adam@rewined.com'))
            if env_recipients:
                recipients = [email.strip() for email in env_recipients.split(',') if email.strip()]
                
                # Add them to the database for next time
                for email in recipients:
                    self.save_recipient_preferences(email, {
                        'name': email.split('@')[0].title(),
                        'active': True
                    })
        
        conn.close()
        return recipients