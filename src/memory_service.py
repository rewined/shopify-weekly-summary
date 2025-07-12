import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MemoryService:
    """Enhanced memory service for Sophie to remember past conversations"""
    
    def __init__(self, db_path: str = None):
        if not db_path:
            db_path = os.getenv('DATABASE_PATH', 'data/feedback.db')
        self.db_path = db_path
        
    def get_conversation_context(self, recipient_email: str, weeks_back: int = 4) -> Dict[str, Any]:
        """Get comprehensive conversation context for a recipient"""
        context = {
            'past_emails': [],
            'replies_received': [],
            'topics_discussed': [],
            'questions_asked': [],
            'feedback_given': [],
            'preferences': {},
            'last_conversation': None
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get past emails sent
            cutoff_date = (datetime.now() - timedelta(weeks=weeks_back)).isoformat()
            
            cursor.execute('''
                SELECT sent_at, insights_sent, questions_asked, report_date
                FROM conversation_history
                WHERE recipient_email = ?
                AND sent_at > ?
                ORDER BY sent_at DESC
                LIMIT 5
            ''', (recipient_email, cutoff_date))
            
            for row in cursor.fetchall():
                sent_at, insights, questions, report_date = row
                
                # Extract key points from the email
                email_summary = self._summarize_email(insights)
                
                context['past_emails'].append({
                    'date': sent_at,
                    'week_of': report_date,
                    'key_points': email_summary,
                    'questions': json.loads(questions) if questions else []
                })
                
                # Track questions asked
                if questions:
                    context['questions_asked'].extend(json.loads(questions))
            
            # Get replies and feedback
            cursor.execute('''
                SELECT received_at, content, context_extracted
                FROM feedback
                WHERE email = ?
                AND received_at > ?
                ORDER BY received_at DESC
            ''', (recipient_email, cutoff_date))
            
            for row in cursor.fetchall():
                received_at, content, extracted = row
                context['replies_received'].append({
                    'date': received_at,
                    'content': content[:200] + '...' if len(content) > 200 else content,
                    'context': json.loads(extracted) if extracted else {}
                })
                
                # Extract feedback themes
                if extracted:
                    extracted_data = json.loads(extracted)
                    if 'track_items' in extracted_data:
                        context['topics_discussed'].extend(extracted_data['track_items'])
            
            # Get recipient preferences
            cursor.execute('''
                SELECT preferences
                FROM recipient_preferences
                WHERE email = ?
            ''', (recipient_email,))
            
            row = cursor.fetchone()
            if row and row[0]:
                context['preferences'] = json.loads(row[0])
            
            # Set last conversation date
            if context['past_emails']:
                context['last_conversation'] = context['past_emails'][0]['date']
            
            # Deduplicate topics and questions
            context['topics_discussed'] = list(set(context['topics_discussed']))
            context['questions_asked'] = list(set(context['questions_asked']))[-10:]  # Keep last 10 unique
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
        finally:
            conn.close()
        
        return context
    
    def _summarize_email(self, email_content: str) -> List[str]:
        """Extract key points from an email for memory"""
        key_points = []
        
        if not email_content:
            return key_points
        
        # Look for performance mentions
        import re
        
        # Revenue mentions
        revenue_matches = re.findall(r'\$[\d,]+(?:\.\d{2})?\s*(?:in\s+)?(?:revenue|sales)', email_content, re.IGNORECASE)
        key_points.extend(revenue_matches[:2])
        
        # Percentage mentions
        percent_matches = re.findall(r'(\d+(?:\.\d+)?%)\s+(?:of|above|below|increase|decrease|growth)', email_content, re.IGNORECASE)
        key_points.extend([f"{match} performance" for match in percent_matches[:2]])
        
        # Product mentions
        product_matches = re.findall(r'(?:top|best)[\s\w]*(?:product|seller|item)[\s\w]*(?:was|were|is|are)\s+([^.]+)', email_content, re.IGNORECASE)
        key_points.extend([f"Top: {match.strip()}" for match in product_matches[:1]])
        
        # Store mentions
        if 'charleston' in email_content.lower():
            charleston_match = re.search(r'charleston[^.]*(?:hit|achieved|reached|made)[^.]+', email_content, re.IGNORECASE)
            if charleston_match:
                key_points.append(charleston_match.group(0))
        
        if 'boston' in email_content.lower():
            boston_match = re.search(r'boston[^.]*(?:hit|achieved|reached|made)[^.]+', email_content, re.IGNORECASE)
            if boston_match:
                key_points.append(boston_match.group(0))
        
        return key_points[:5]  # Limit to 5 key points
    
    def save_enhanced_conversation(self, recipient_email: str, email_content: str, 
                                 analytics_data: Dict, questions: List[str], 
                                 topics: List[str]) -> None:
        """Save conversation with enhanced metadata for better memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create enhanced conversation table if needed
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient_email TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    week_start TEXT,
                    week_end TEXT,
                    revenue_total REAL,
                    revenue_charleston REAL,
                    revenue_boston REAL,
                    goal_charleston REAL,
                    goal_boston REAL,
                    performance_charleston_pct REAL,
                    performance_boston_pct REAL,
                    top_products TEXT,
                    key_topics TEXT,
                    questions_asked TEXT,
                    email_excerpt TEXT
                )
            ''')
            
            # Extract key metrics
            charleston_data = analytics_data.get('current_week_by_location', {}).get('charleston', {})
            boston_data = analytics_data.get('current_week_by_location', {}).get('boston', {})
            goals = analytics_data.get('goals', {})
            conversion = analytics_data.get('conversion_metrics', {})
            
            # Save enhanced memory
            cursor.execute('''
                INSERT INTO conversation_memory (
                    recipient_email, week_start, week_end,
                    revenue_total, revenue_charleston, revenue_boston,
                    goal_charleston, goal_boston,
                    performance_charleston_pct, performance_boston_pct,
                    top_products, key_topics, questions_asked, email_excerpt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipient_email,
                analytics_data.get('week_start'),
                analytics_data.get('week_end'),
                analytics_data.get('total_revenue', 0),
                charleston_data.get('total_revenue', 0),
                boston_data.get('total_revenue', 0),
                goals.get('charleston', {}).get('revenue_goal', 0),
                goals.get('boston', {}).get('revenue_goal', 0),
                conversion.get('charleston', {}).get('revenue_vs_goal_pct', 0),
                conversion.get('boston', {}).get('revenue_vs_goal_pct', 0),
                json.dumps(self._get_top_products(analytics_data)),
                json.dumps(topics),
                json.dumps(questions),
                email_content[:500]  # Save excerpt
            ))
            
            conn.commit()
            logger.info(f"Saved enhanced conversation memory for {recipient_email}")
            
        except Exception as e:
            logger.error(f"Error saving enhanced conversation: {e}")
        finally:
            conn.close()
    
    def _get_top_products(self, analytics_data: Dict) -> List[str]:
        """Extract top product names"""
        products = analytics_data.get('product_performance', [])
        return [p['product'] for p in products[:3]]
    
    def get_performance_trends(self, recipient_email: str) -> Dict[str, Any]:
        """Get performance trends from past conversations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        trends = {
            'revenue_trend': [],
            'charleston_trend': [],
            'boston_trend': [],
            'topics_evolution': []
        }
        
        try:
            cursor.execute('''
                SELECT week_start, revenue_total, revenue_charleston, revenue_boston,
                       performance_charleston_pct, performance_boston_pct, key_topics
                FROM conversation_memory
                WHERE recipient_email = ?
                ORDER BY week_start DESC
                LIMIT 8
            ''', (recipient_email,))
            
            for row in cursor.fetchall():
                week_start, total, charleston, boston, chs_pct, bos_pct, topics = row
                
                trends['revenue_trend'].append({
                    'week': week_start,
                    'total': total,
                    'vs_goal': (chs_pct + bos_pct) / 2 if chs_pct and bos_pct else None
                })
                
                trends['charleston_trend'].append({
                    'week': week_start,
                    'revenue': charleston,
                    'vs_goal_pct': chs_pct
                })
                
                trends['boston_trend'].append({
                    'week': week_start,
                    'revenue': boston,
                    'vs_goal_pct': bos_pct
                })
                
                if topics:
                    trends['topics_evolution'].extend(json.loads(topics))
            
            # Reverse to chronological order
            for key in ['revenue_trend', 'charleston_trend', 'boston_trend']:
                trends[key].reverse()
            
        except Exception as e:
            logger.error(f"Error getting performance trends: {e}")
        finally:
            conn.close()
        
        return trends