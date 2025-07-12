import os
from typing import Dict, List, Any
import anthropic
import json
from datetime import datetime


class ConversationalInsights:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        self.conversation_history = self._load_conversation_history()
    
    def _load_conversation_history(self):
        """Load past conversation context"""
        history_file = os.path.join('data', 'conversation_history.json')
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_conversation_history(self):
        """Save conversation history for future reference"""
        history_file = os.path.join('data', 'conversation_history.json')
        os.makedirs('data', exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(self.conversation_history[-10:], f)  # Keep last 10 conversations
    
    def generate_insights(self, analytics_data: Dict, recipient_name: str, feedback_context: Dict = None) -> Dict[str, Any]:
        """Generate conversational insights using Claude"""
        
        # Build context from past conversations
        context = ""
        if feedback_context:
            context = f"\nPast feedback from {recipient_name}: {json.dumps(feedback_context, indent=2)}"
        
        if self.conversation_history:
            recent = self.conversation_history[-3:]
            context += f"\n\nRecent conversation topics: {json.dumps(recent, indent=2)}"
        
        # Do web search for local events that might affect sales
        event_context = ""
        try:
            week_start_str = analytics_data.get('week_start', '')
            if week_start_str:
                week_date = datetime.strptime(week_start_str, '%Y-%m-%d')
                # In production, you would do actual web searches here
                event_context += f"\n\nLocal events to consider:"
                event_context += f"\n- Charleston: Check for 2nd Sunday on King Street, festivals, weather"
                event_context += f"\n- Boston: Check for Open Newbury events, weather patterns"
        except:
            pass
        
        # Get current day and time for more natural context
        current_time = datetime.now()
        day_of_week = current_time.strftime('%A')
        time_of_day = 'morning' if current_time.hour < 12 else 'afternoon' if current_time.hour < 17 else 'evening'
        
        prompt = f"""You are Sophie Blake, a 23-year-old intern at Rewined working on Candlefish analytics. You're smart, 
        enthusiastic, and genuinely enjoy digging into data. You've been at Rewined for 3 months now and are getting 
        comfortable with {recipient_name}'s communication style.
        
        It's {day_of_week} {time_of_day}. You're writing this email from your desk at Rewined's office.
        
        CONTEXT ABOUT THE BUSINESS:
        - Two stores: Charleston (270 King St, established 2014) and Boston (110 Newbury St, opened July 2024)
        - Products: Candle Library (cf##### SKUs), Match Bar, Workshops, Gift items
        - Goals tracked in Google Sheets with targets for traffic, conversion, average ticket
        - Workshop occupancy targets: Charleston 75%, Boston 60%
        
        THIS WEEK'S DATA:
        {json.dumps(analytics_data, indent=2)}
        
        {context}
        {event_context}
        
        Write a COMPLETE EMAIL to {recipient_name} about this week's performance. Not just insights - write the full email 
        from greeting to sign-off. Make it sound like YOU actually wrote it, not a template. Mix up your writing style:
        
        - Sometimes start with the weather or something happening in your life
        - Sometimes jump right into an interesting finding
        - Sometimes mention what you were doing when you noticed something in the data
        - Use different greetings (Hey, Hi, Good morning, etc.)
        - Vary your sign-offs (Best, Thanks, Talk soon, etc.)
        - Write like you're actually typing an email - natural pauses, real enthusiasm, genuine questions
        
        Include:
        - How the stores performed vs goals (but work it in naturally)
        - Any interesting patterns or surprises you found
        - 2-3 genuine questions that come from actually looking at the data
        
        Remember: You're writing ONE complete email. Make it feel real and different each time.
        
        Format as JSON with keys: "full_email" and "questions" (extract the questions separately for tracking)
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                temperature=0.9,  # Higher temperature for more variation
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            content = response.content[0].text
            
            # Try to parse as JSON
            try:
                result = json.loads(content)
                # Handle new format with full_email
                if 'full_email' in result:
                    result['insights_text'] = result['full_email']
                # Ensure we have the right keys
                if 'insights_html' in result and 'insights_text' not in result:
                    result['insights_text'] = result['insights_html']
            except json.JSONDecodeError:
                # Fallback if not valid JSON
                result = {
                    "insights_text": content,
                    "questions": [
                        "What's been the customer response to your recent changes?",
                        "Are there any special events or promotions you're planning?",
                        "What product categories would you like me to track more closely?"
                    ]
                }
            
            # Save this conversation
            self.conversation_history.append({
                "date": datetime.now().isoformat(),
                "recipient": recipient_name,
                "topics": self._extract_topics(analytics_data),
                "questions_asked": result.get("questions", [])
            })
            self._save_conversation_history()
            
            return result
            
        except Exception as e:
            print(f"Error generating insights: {str(e)}")
            return self._generate_fallback_insights(analytics_data, recipient_name)
    
    def _extract_topics(self, analytics_data: Dict) -> List[str]:
        """Extract key topics from analytics data"""
        topics = []
        
        # Revenue changes
        yoy = analytics_data.get('yoy_changes', {})
        if yoy.get('total_revenue_change', 0) > 20:
            topics.append("significant revenue growth")
        elif yoy.get('total_revenue_change', 0) < -20:
            topics.append("revenue decline")
        
        # Product performance
        top_products = analytics_data.get('product_performance', [])
        if top_products:
            topics.append(f"top product: {top_products[0]['product']}")
        
        # Workshop data
        workshops = analytics_data.get('workshop_analytics', {})
        if workshops.get('attendees', 0) > 0:
            topics.append(f"workshop attendance: {workshops['attendees']}")
        
        return topics
    
    def _generate_fallback_insights(self, analytics_data: Dict, recipient_name: str) -> Dict[str, Any]:
        """Generate fallback insights if Claude API fails"""
        
        current = analytics_data.get('current_week', {})
        yoy = analytics_data.get('yoy_changes', {})
        products = analytics_data.get('product_performance', [])
        
        insights = f"""Looking at this week's performance, you brought in ${current.get('total_revenue', 0):,.2f} from {current.get('order_count', 0)} orders. {"That's up " + str(abs(yoy.get('total_revenue_change', 0))) + "% from the same week last year." if yoy.get('total_revenue_change', 0) > 0 else "That's down " + str(abs(yoy.get('total_revenue_change', 0))) + "% from the same week last year."}

{"Your top seller was " + products[0]['product'] + ", " if products else ""}{"and c" if products else "C"}ustomers spent an average of ${current.get('avg_order_value', 0):.2f} per order.

Based on these numbers, {"revenue is trending well above last year" if yoy.get('total_revenue_change', 0) > 10 else "revenue could use some attention" if yoy.get('total_revenue_change', 0) < -10 else "revenue is holding steady"}. The average order value {"shows customers are finding multiple items they like" if current.get('avg_order_value', 0) > 80 else "might benefit from some upselling opportunities"}."""
        
        questions = [
            "Were there any special events or promotions running this week that would have affected these numbers?",
            "Are there any specific product categories or workshops you'd like me to track more closely?",
            "What are your main priorities for improving store performance in the coming weeks?"
        ]
        
        return {
            "insights_text": insights,
            "questions": questions
        }
    
    def process_feedback(self, feedback_text: str, sender_email: str) -> Dict[str, Any]:
        """Process feedback from email replies"""
        
        prompt = f"""Analyze this feedback from a Candlefish customer about their business:
        
        Feedback: {feedback_text}
        
        Extract:
        1. Key business context (events, promotions, challenges)
        2. Specific items or metrics they want tracked
        3. Preferences about reporting
        4. Any questions they asked
        
        Format as JSON with keys: "context", "track_items", "preferences", "questions"
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            
            try:
                result = json.loads(content)
            except:
                result = {
                    "context": feedback_text,
                    "track_items": [],
                    "preferences": {},
                    "questions": []
                }
            
            # Save feedback context
            context_file = os.path.join('data', 'feedback_context.json')
            existing_context = {}
            
            if os.path.exists(context_file):
                try:
                    with open(context_file, 'r') as f:
                        existing_context = json.load(f)
                except:
                    pass
            
            # Merge new context
            if 'track_items' in result:
                existing_context.setdefault('track_items', []).extend(result['track_items'])
                existing_context['track_items'] = list(set(existing_context['track_items']))
            
            if 'context' in result:
                existing_context.setdefault('business_context', []).append({
                    'date': datetime.now().isoformat(),
                    'context': result['context']
                })
            
            with open(context_file, 'w') as f:
                json.dump(existing_context, f)
            
            return result
            
        except Exception as e:
            print(f"Error processing feedback: {str(e)}")
            return {
                "context": feedback_text,
                "track_items": [],
                "preferences": {},
                "questions": []
            }