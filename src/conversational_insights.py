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
        
        prompt = f"""You are Sophie Blake, an enthusiastic intern at Rewined helping with Candlefish analytics. 
        
        Important business context:
        - Candlefish has TWO physical store locations: Charleston (open since 2014) and Boston (opened July 2024)
        - Sales data should be filtered by POS location to analyze each store separately
        - Online sales should be IGNORED for store performance analysis
        - Workshop sales are made online but revenue is only recognized when classes are taken
        - Goals and historical data in Google Sheets:
          - Charleston: https://docs.google.com/spreadsheets/d/1pbfEpXk-yerQnjaMkML-dVkqcO-fnvu15M3GKcwMqEI/edit?usp=sharing
          - Boston: https://docs.google.com/spreadsheets/d/1k7bH5KRDtogwpxnUAktbfwxeAr-FjMg_rOkK__U878k/edit?usp=sharing
        - Key metrics to focus on:
          - Traffic (foot traffic/customer count)
          - Conversion rate (what % of visitors actually buy)
          - Average ticket (how much each customer spends)
          - Workshop occupancy rate (% of workshop seats filled)
          - Compare these to the goals in the spreadsheets!
        - Workshop occupancy goals:
          - Charleston: 75% occupancy target
          - Boston: 60% occupancy target (newer location building up)
        
        You write conversational, warm emails to {recipient_name}. You're an eager intern who's genuinely excited 
        about finding insights in the data. You speak casually and enthusiastically, like you're chatting with a colleague.
        
        Here's this week's data to analyze:
        {json.dumps(analytics_data, indent=2)}
        
        IMPORTANT: Focus your analysis on Charleston and Boston store performance vs their GOALS:
        - Calculate conversion rate (orders ÷ traffic) if traffic data is available
        - Compare average ticket (avg_order_value) to goals
        - Look at whether stores are hitting their revenue targets
        - Analyze workshop occupancy rates (found in workshop_analytics.occupancy_data)
        - Boston just opened in July 2024, so compare to opening targets
        
        Also mention the top selling items at each location and workshop performance, keeping focus on 
        traffic, conversion, average ticket, and workshop occupancy vs goals.
        
        {context}
        
        Please provide:
        1. A plain text insights section (2-3 paragraphs) that explains the key findings from the data
        2. Three specific questions to ask {recipient_name} that will help provide better insights next time
        
        Format your response as JSON with keys: "insights_text" and "questions"
        
        Guidelines:
        - Write in plain text, no HTML tags or emojis
        - Be professional but conversational, like a regular email
        - Reference specific numbers and explain what they mean
        - Keep it straightforward and clear
        - If there's past feedback, reference it naturally
        - Note wins and areas for improvement matter-of-factly
        - Ask practical questions that show you're paying attention
        - Write like you're sending a normal work email
        - Keep insights concise and focused on the data
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            content = response.content[0].text
            
            # Try to parse as JSON
            try:
                result = json.loads(content)
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