import os
from typing import Dict, List, Any
import anthropic
import json
import re
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
        
        # Build enhanced context from memory service
        context = ""
        memory_context = {}
        
        try:
            from .memory_service import MemoryService
            memory = MemoryService()
            memory_context = memory.get_conversation_context(
                analytics_data.get('recipient_email', f'{recipient_name.lower()}@candlefish.com')
            )
            
            # Build rich context for Sophie
            if memory_context['past_emails']:
                context += f"\n\nPAST CONVERSATIONS WITH {recipient_name.upper()}:"
                for email in memory_context['past_emails'][:3]:
                    context += f"\n- Week of {email['week_of']}: {', '.join(email['key_points'][:2])}"
                    if email['questions']:
                        context += f"\n  Asked: {email['questions'][0]}"
            
            if memory_context['replies_received']:
                context += f"\n\nRECENT REPLIES FROM {recipient_name.upper()}:"
                for reply in memory_context['replies_received'][:2]:
                    context += f"\n- {reply['content']}"
            
            if memory_context['topics_discussed']:
                context += f"\n\nTOPICS {recipient_name.upper()} CARES ABOUT: {', '.join(memory_context['topics_discussed'])}"
            
            # Get performance trends
            trends = memory.get_performance_trends(analytics_data.get('recipient_email', f'{recipient_name.lower()}@candlefish.com'))
            if trends['revenue_trend'] and len(trends['revenue_trend']) > 1:
                context += f"\n\nPERFORMANCE TREND:"
                context += f"\n- Last week: ${trends['revenue_trend'][-2]['total']:,.0f}"
                context += f"\n- This week: ${trends['revenue_trend'][-1]['total']:,.0f}"
                
        except Exception as e:
            print(f"Could not load enhanced memory context: {e}")
            # Fall back to basic context
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
        
        prompt = f"""You are Sophie Blake, a 23-year-old intern working on analytics for both Rewined and Candlefish brands. 
        You're smart, enthusiastic, and genuinely enjoy digging into data. You've been working for 3 months now and are getting 
        comfortable with {recipient_name}'s communication style.
        
        It's {day_of_week} {time_of_day}. You're analyzing this week's performance data.
        
        IMPORTANT CONTEXT ABOUT THE BUSINESS:
        - Rewined and Candlefish are SEPARATE brands both owned by {recipient_name}
        - REWINED: A candle brand that sells wholesale and online only (no retail stores)
        - CANDLEFISH: A separate brand with:
          - Two retail stores: Charleston (270 King St, established 2014) and Boston (110 Newbury St, opened August 1, 2024)
          - Online store
          - Wholesale business
          - Sells some Rewined candles in their stores (Rewined is a wholesale supplier to Candlefish)
        - Products at Candlefish stores: Candle Library (cf##### SKUs), Match Bar, Workshops, Gift items, some Rewined candles
        - You regularly check the monthly sales data in the Google Sheets
        - Boston store only started selling around August 1, 2024 - be skeptical of huge YoY growth numbers
        - Goals are pulled from Google Sheets monthly forecasts and converted to weekly targets
        - Charleston monthly forecast sheet: 1pbfEpXk-yerQnjaMkML-dVkqcO-fnvu15M3GKcwMqEI
        - Boston monthly forecast sheet: 1k7bH5KRDtogwpxnUAktbfwxeAr-FjMg_rOkK__U878k
        - Workshop occupancy targets: Charleston 75%, Boston 60%
        
        THIS WEEK'S DATA:
        {json.dumps(analytics_data, indent=2)}
        
        {context}
        {event_context}
        
        Write a COMPLETE EMAIL to {recipient_name} about this week's performance. Not just insights - write the full email 
        from greeting to sign-off. Make it sound like YOU actually wrote it, not a template. Mix up your writing style:
        
        - Sometimes start with what you're working on or something happening at the office
        - Sometimes jump right into an interesting finding
        - Sometimes mention what you were doing when you noticed something in the data
        - Use different greetings (Hey, Hi, Good morning, etc.)
        - Vary your sign-offs (Best, Thanks, Talk soon, etc.)
        - Write like you're actually typing an email - natural pauses, real enthusiasm, genuine questions
        - AVOID making specific weather references unless you have actual weather data
        
        MEMORY & CONTINUITY:
        - Reference past conversations naturally (e.g., "Last week you asked about..." or "Following up on...")
        - If performance changed significantly from last week, mention it
        - If they gave feedback or asked questions, acknowledge and respond
        - Build on previous topics - don't treat each email as the first one
        - Show you remember what matters to them
        
        Include:
        - How the stores performed vs goals (but work it in naturally)
        - Any interesting patterns or surprises you found
        - 2-3 genuine questions that come from actually looking at the data
        - Reference checking the monthly tab in the spreadsheets when relevant
        
        IMPORTANT DATA INTERPRETATION:
        - If you see YoY growth over 1000%, question if it's a data error or comparison issue
        - Boston didn't exist last year, so YoY comparisons are meaningless - acknowledge this
        - Always sanity-check extreme numbers and mention if something seems off
        - When mentioning specific numbers (revenue, orders, percentages), make sure they come from the actual data provided
        - If you do calculations (like $408/12 units), double-check your math
        - Don't make assumptions about data that isn't provided (like specific product revenues)
        - Keep emails complete - don't cut off mid-sentence
        
        Remember: You're writing ONE complete email. Make it feel real and different each time.
        
        Format as JSON with keys: "full_email" and "questions" (extract the questions separately for tracking)
        
        IMPORTANT: Return ONLY the JSON object, no markdown code blocks, no ```json tags, just the raw JSON.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,  # Balanced between completeness and speed
                temperature=0.9,  # Higher temperature for more variation
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            content = response.content[0].text
            
            # Remove markdown code blocks if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # Try to parse as JSON
            try:
                # Clean up control characters that cause JSON parsing issues
                cleaned_content = content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                # Try the cleaned version first
                try:
                    result = json.loads(cleaned_content)
                except:
                    # If that fails, try the original
                    result = json.loads(content)
                print(f"Successfully parsed JSON with keys: {result.keys()}")
                
                # Detailed logging to show Sophie's data sources and calculations
                email_text = result.get('full_email', '')
                if email_text:
                    print(f"\n=== SOPHIE'S EMAIL ANALYSIS ===")
                    print(f"Email generated successfully ({len(email_text)} chars)")
                    
                    # Extract numbers Sophie mentions in her email
                    import re
                    revenue_mentions = re.findall(r'\$([0-9,]+(?:\.[0-9]{2})?)', email_text)
                    percentage_mentions = re.findall(r'([0-9]+(?:\.[0-9]+)?%)', email_text)
                    order_mentions = re.findall(r'([0-9]+) orders?', email_text, re.IGNORECASE)
                    
                    print(f"Numbers Sophie mentioned:")
                    print(f"  - Revenue figures: ${', $'.join(revenue_mentions)}")
                    print(f"  - Percentages: {', '.join(percentage_mentions)}")
                    print(f"  - Order counts: {', '.join(order_mentions)} orders")
                    
                    # Show the actual Shopify data Sophie had access to
                    print(f"\nSOURCE DATA (from Shopify API):")
                    current_week = analytics_data.get('current_week_by_location', {})
                    charleston_data = current_week.get('charleston', {})
                    boston_data = current_week.get('boston', {})
                    all_data = current_week.get('all', {})
                    
                    print(f"  Charleston: ${charleston_data.get('total_revenue', 0):.2f} revenue, {charleston_data.get('order_count', 0)} orders")
                    print(f"  Boston: ${boston_data.get('total_revenue', 0):.2f} revenue, {boston_data.get('order_count', 0)} orders")
                    print(f"  Combined: ${all_data.get('total_revenue', 0):.2f} revenue, {all_data.get('order_count', 0)} orders")
                    
                    # Show YoY data
                    yoy_changes = analytics_data.get('yoy_changes', {})
                    if yoy_changes:
                        print(f"\nYEAR-OVER-YEAR DATA (from Shopify API):")
                        charleston_yoy = yoy_changes.get('charleston', {})
                        boston_yoy = yoy_changes.get('boston', {})
                        all_yoy = yoy_changes.get('all', {})
                        print(f"  Charleston revenue change: {charleston_yoy.get('total_revenue_change', 'N/A')}%")
                        print(f"  Boston revenue change: {boston_yoy.get('total_revenue_change', 'N/A')}%") 
                        print(f"  Combined revenue change: {all_yoy.get('total_revenue_change', 'N/A')}%")
                    
                    # Show goals data if available
                    goals = analytics_data.get('goals', {})
                    conversion_metrics = analytics_data.get('conversion_metrics', {})
                    if goals and conversion_metrics:
                        print(f"\nGOALS DATA (from Google Sheets service):")
                        charleston_goals = goals.get('charleston', {})
                        boston_goals = goals.get('boston', {})
                        charleston_metrics = conversion_metrics.get('charleston', {})
                        boston_metrics = conversion_metrics.get('boston', {})
                        
                        print(f"  Charleston: {charleston_metrics.get('revenue_vs_goal_pct', 'N/A')}% of ${charleston_goals.get('revenue_goal', 'N/A'):.0f} weekly goal")
                        print(f"    Monthly target: ${charleston_goals.get('monthly_revenue_goal', 'N/A'):.0f} ({charleston_goals.get('source_month', 'N/A')})")
                        print(f"  Boston: {boston_metrics.get('revenue_vs_goal_pct', 'N/A')}% of ${boston_goals.get('revenue_goal', 'N/A'):.0f} weekly goal") 
                        print(f"    Monthly target: ${boston_goals.get('monthly_revenue_goal', 'N/A'):.0f} ({boston_goals.get('source_month', 'N/A')})")
                        print(f"  Source: {goals.get('source', 'Unknown')}")
                        print(f"  NOTE: Weekly goals calculated from monthly forecast data")
                    
                    # Show product performance
                    products = analytics_data.get('product_performance', [])
                    if products:
                        print(f"\nTOP PRODUCTS (from Shopify API):")
                        for i, product in enumerate(products[:3]):
                            print(f"  {i+1}. {product['product'][:30]}... - {product['quantity']} units, ${product['revenue']:.2f}")
                    
                    print("=== END ANALYSIS ===\n")
                else:
                    print("Warning: No email text generated")
                
                # Handle new format with full_email
                if 'full_email' in result:
                    result['insights_text'] = result['full_email']
                # Ensure we have the right keys
                if 'insights_html' in result and 'insights_text' not in result:
                    result['insights_text'] = result['insights_html']
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Content was: {content[:200]}...")
                
                # Try multiple extraction methods
                email_text = None
                questions = []
                
                # Method 1: Try to extract using regex
                if '"full_email"' in content:
                    email_match = re.search(r'"full_email"\s*:\s*"([^"]+(?:\\.[^"]+)*)"', content, re.DOTALL)
                    if email_match:
                        email_text = email_match.group(1)
                        # Unescape the string
                        email_text = email_text.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                        print("Extracted email using regex")
                        
                        # Try to extract questions too
                        questions_match = re.search(r'"questions"\s*:\s*\[(.*?)\]', content, re.DOTALL)
                        if questions_match:
                            questions_str = questions_match.group(1)
                            # Extract individual questions
                            question_matches = re.findall(r'"([^"]+)"', questions_str)
                            questions = question_matches
                
                # Method 2: Try to find and parse JSON object
                if not email_text and '"full_email"' in content:
                    try:
                        # Find the JSON object in the content
                        start = content.find('{')
                        end = content.rfind('}') + 1
                        if start >= 0 and end > start:
                            json_str = content[start:end]
                            parsed = json.loads(json_str)
                            if 'full_email' in parsed:
                                email_text = parsed['full_email']
                                questions = parsed.get('questions', [])
                                print("Extracted email by parsing JSON object")
                    except Exception as parse_error:
                        print(f"Failed to extract JSON object: {parse_error}")
                
                # Set the result
                if email_text:
                    result = {
                        "insights_text": email_text,
                        "questions": questions if questions else []
                    }
                else:
                    # Final fallback - just use the content as is
                    print("Using content as-is (fallback)")
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