from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from collections import defaultdict
import os
import json


class ShopifyAnalytics:
    def __init__(self, shopify_service):
        self.shopify = shopify_service
        self.feedback_context = self._load_feedback_context()
    
    def _load_feedback_context(self):
        """Load historical feedback and context from database"""
        context_file = os.path.join('data', 'feedback_context.json')
        if os.path.exists(context_file):
            try:
                with open(context_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def analyze_weekly_data(self, week_start: datetime = None) -> Dict[str, Any]:
        """Analyze data for a specific week, defaulting to last week"""
        if not week_start:
            # Default to last Monday
            today = datetime.now()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday + 7)
        
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # Get current week data
        current_orders = self.shopify.get_orders_for_period(week_start, week_end)
        
        # Get previous year data for comparison
        prev_year_start = week_start - timedelta(days=365)
        prev_year_end = week_end - timedelta(days=365)
        prev_year_orders = self.shopify.get_orders_for_period(prev_year_start, prev_year_end)
        
        # Separate orders by location (POS vs Online)
        current_charleston = [o for o in current_orders if self._is_charleston_pos(o)]
        current_boston = [o for o in current_orders if self._is_boston_pos(o)]
        current_online = [o for o in current_orders if self._is_online_order(o)]
        
        prev_charleston = [o for o in prev_year_orders if self._is_charleston_pos(o)]
        prev_boston = [o for o in prev_year_orders if self._is_boston_pos(o)]
        prev_online = [o for o in prev_year_orders if self._is_online_order(o)]
        
        # Process the data by location
        current_metrics = {
            'all': self._calculate_metrics(current_orders),
            'charleston': self._calculate_metrics(current_charleston),
            'boston': self._calculate_metrics(current_boston),
            'online': self._calculate_metrics(current_online)
        }
        prev_year_metrics = {
            'all': self._calculate_metrics(prev_year_orders),
            'charleston': self._calculate_metrics(prev_charleston),
            'boston': self._calculate_metrics(prev_boston),
            'online': self._calculate_metrics(prev_online)
        }
        
        # Calculate year-over-year changes
        yoy_changes = self._calculate_yoy_changes(current_metrics, prev_year_metrics)
        
        # Get product performance
        product_performance = self._analyze_product_performance(current_orders)
        
        # Get workshop analytics
        workshop_data = self._analyze_workshops(current_orders)
        
        # Get customer insights
        customer_insights = self._analyze_customers(current_orders)
        
        # Identify trends and patterns
        trends = self._identify_trends(current_orders, prev_year_orders)
        
        return {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'current_week': current_metrics['all'],  # Keep backward compatibility
            'current_week_by_location': current_metrics,
            'previous_year': prev_year_metrics['all'],  # Keep backward compatibility
            'previous_year_by_location': prev_year_metrics,
            'yoy_changes': yoy_changes,
            'product_performance': product_performance,
            'workshop_analytics': workshop_data,
            'customer_insights': customer_insights,
            'trends': trends,
            'total_revenue': current_metrics['all']['total_revenue'],
            'total_orders': current_metrics['all']['order_count'],
            'avg_order_value': current_metrics['all']['avg_order_value']
        }
    
    def _calculate_metrics(self, orders: List[Dict]) -> Dict[str, Any]:
        """Calculate basic metrics from orders"""
        if not orders:
            return {
                'order_count': 0,
                'total_revenue': 0,
                'avg_order_value': 0,
                'total_items_sold': 0,
                'unique_customers': 0,
                'repeat_customers': 0
            }
        
        df = pd.DataFrame(orders)
        
        total_revenue = df['total_price'].sum()
        order_count = len(df)
        avg_order_value = total_revenue / order_count if order_count > 0 else 0
        
        # Count total items
        total_items = sum(
            sum(item['quantity'] for item in order['line_items'])
            for order in orders
        )
        
        # Customer analysis
        customer_orders = defaultdict(int)
        for order in orders:
            email = order.get('customer_email', 'guest')
            customer_orders[email] += 1
        
        unique_customers = len(customer_orders)
        repeat_customers = sum(1 for count in customer_orders.values() if count > 1)
        
        return {
            'order_count': order_count,
            'total_revenue': total_revenue,
            'avg_order_value': avg_order_value,
            'total_items_sold': total_items,
            'unique_customers': unique_customers,
            'repeat_customers': repeat_customers
        }
    
    def _calculate_yoy_changes(self, current: Dict, previous: Dict) -> Dict[str, Any]:
        """Calculate year-over-year percentage changes"""
        changes = {}
        
        # Calculate changes for each location
        for location in ['all', 'charleston', 'boston', 'online']:
            changes[location] = {}
            current_loc = current.get(location, {})
            previous_loc = previous.get(location, {})
            
            for metric in ['total_revenue', 'order_count', 'avg_order_value', 'total_items_sold']:
                if previous_loc.get(metric, 0) > 0:
                    change = ((current_loc.get(metric, 0) - previous_loc.get(metric, 0)) / previous_loc.get(metric, 0)) * 100
                    changes[location][f'{metric}_change'] = round(change, 1)
                else:
                    changes[location][f'{metric}_change'] = 100 if current_loc.get(metric, 0) > 0 else 0
        
        # Keep backward compatibility - return 'all' metrics at root level
        for metric, value in changes['all'].items():
            changes[metric] = value
        
        return changes
    
    def _analyze_product_performance(self, orders: List[Dict]) -> List[Dict]:
        """Analyze which products performed best"""
        product_sales = defaultdict(lambda: {'quantity': 0, 'revenue': 0, 'orders': 0})
        
        for order in orders:
            for item in order['line_items']:
                title = item['title']
                product_sales[title]['quantity'] += item['quantity']
                product_sales[title]['revenue'] += item['price'] * item['quantity']
                product_sales[title]['orders'] += 1
        
        # Convert to list and sort by revenue
        products = []
        for title, data in product_sales.items():
            products.append({
                'product': title,
                'quantity_sold': data['quantity'],
                'revenue': data['revenue'],
                'order_count': data['orders'],
                'avg_price': data['revenue'] / data['quantity'] if data['quantity'] > 0 else 0
            })
        
        return sorted(products, key=lambda x: x['revenue'], reverse=True)[:10]
    
    def _analyze_workshops(self, orders: List[Dict]) -> Dict[str, Any]:
        """Analyze workshop-specific data"""
        workshop_orders = self.shopify.get_workshop_orders(
            datetime.strptime(orders[0]['created_at'], '%Y-%m-%dT%H:%M:%S%z') if orders else datetime.now(),
            datetime.strptime(orders[-1]['created_at'], '%Y-%m-%dT%H:%M:%S%z') if orders else datetime.now()
        )
        
        if not workshop_orders:
            return {
                'total_workshops': 0,
                'workshop_revenue': 0,
                'attendees': 0,
                'popular_workshops': []
            }
        
        workshop_types = defaultdict(lambda: {'count': 0, 'revenue': 0, 'attendees': 0})
        
        for order in workshop_orders:
            for item in order['line_items']:
                if 'workshop' in item['title'].lower() or 'class' in item['title'].lower():
                    workshop_types[item['title']]['count'] += 1
                    workshop_types[item['title']]['revenue'] += item['price'] * item['quantity']
                    workshop_types[item['title']]['attendees'] += item['quantity']
        
        popular_workshops = [
            {
                'name': name,
                'sessions': data['count'],
                'revenue': data['revenue'],
                'attendees': data['attendees']
            }
            for name, data in sorted(workshop_types.items(), key=lambda x: x[1]['revenue'], reverse=True)[:5]
        ]
        
        total_revenue = sum(data['revenue'] for data in workshop_types.values())
        total_attendees = sum(data['attendees'] for data in workshop_types.values())
        
        return {
            'total_workshops': len(workshop_orders),
            'workshop_revenue': total_revenue,
            'attendees': total_attendees,
            'popular_workshops': popular_workshops
        }
    
    def _analyze_customers(self, orders: List[Dict]) -> Dict[str, Any]:
        """Analyze customer behavior"""
        customer_data = defaultdict(lambda: {'orders': 0, 'revenue': 0, 'items': 0})
        
        for order in orders:
            customer = order.get('customer_email', 'guest')
            customer_data[customer]['orders'] += 1
            customer_data[customer]['revenue'] += order['total_price']
            customer_data[customer]['items'] += sum(item['quantity'] for item in order['line_items'])
        
        # Find VIP customers (top spenders)
        vip_customers = sorted(
            [(email, data) for email, data in customer_data.items()],
            key=lambda x: x[1]['revenue'],
            reverse=True
        )[:5]
        
        # Calculate customer segments
        segments = {
            'new_customers': sum(1 for data in customer_data.values() if data['orders'] == 1),
            'repeat_customers': sum(1 for data in customer_data.values() if data['orders'] > 1),
            'vip_customers': [
                {
                    'email': email.split('@')[0] + '@***' if '@' in email else email,
                    'orders': data['orders'],
                    'revenue': data['revenue']
                }
                for email, data in vip_customers
            ]
        }
        
        return segments
    
    def _identify_trends(self, current_orders: List[Dict], prev_year_orders: List[Dict]) -> List[str]:
        """Identify notable trends and patterns"""
        trends = []
        
        # Check if feedback context mentions specific things to track
        if 'track_items' in self.feedback_context:
            for item in self.feedback_context['track_items']:
                relevant_orders = [o for o in current_orders if any(item.lower() in li['title'].lower() for li in o['line_items'])]
                if relevant_orders:
                    trends.append(f"As requested, I tracked {item} - found {len(relevant_orders)} orders this week")
        
        # Day of week analysis
        if current_orders:
            df = pd.DataFrame(current_orders)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['day_of_week'] = df['created_at'].dt.day_name()
            
            best_day = df.groupby('day_of_week')['total_price'].sum().idxmax()
            trends.append(f"{best_day} was your best sales day")
        
        # Product category trends
        current_categories = defaultdict(int)
        for order in current_orders:
            for item in order['line_items']:
                if 'candle' in item['title'].lower():
                    current_categories['candles'] += item['quantity']
                elif 'workshop' in item['title'].lower() or 'class' in item['title'].lower():
                    current_categories['workshops'] += item['quantity']
                elif 'gift' in item['title'].lower():
                    current_categories['gifts'] += item['quantity']
        
        for category, count in current_categories.items():
            if count > 10:
                trends.append(f"{category.capitalize()} are trending with {count} units sold")
        
        return trends
    
    def _is_charleston_pos(self, order: Dict) -> bool:
        """Check if order is from Charleston POS"""
        # Check tags for location identifiers
        tags = order.get('tags', [])
        note = order.get('note', '').lower()
        
        # Common indicators for Charleston POS
        return any([
            'charleston' in ' '.join(tags).lower(),
            'chs' in ' '.join(tags).lower(),
            'pos' in ' '.join(tags).lower() and 'boston' not in ' '.join(tags).lower(),
            'charleston' in note,
            # Check if source is POS and not tagged as Boston
            order.get('source_name', '').lower() == 'pos' and not self._is_boston_pos(order)
        ])
    
    def _is_boston_pos(self, order: Dict) -> bool:
        """Check if order is from Boston POS"""
        # Check tags for location identifiers
        tags = order.get('tags', [])
        note = order.get('note', '').lower()
        
        # Common indicators for Boston POS
        return any([
            'boston' in ' '.join(tags).lower(),
            'bos' in ' '.join(tags).lower(),
            'boston' in note
        ])
    
    def _is_online_order(self, order: Dict) -> bool:
        """Check if order is from online store"""
        source = order.get('source_name', '').lower()
        
        # Common indicators for online orders
        return source in ['web', 'online_store', 'shopify'] and not self._is_charleston_pos(order) and not self._is_boston_pos(order)
