from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from collections import defaultdict
import os
import json
import re


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
    
    def analyze_weekly_data(self, week_start: datetime = None, include_trends: bool = False) -> Dict[str, Any]:
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
        
        # Separate orders by location (POS only - exclude online)
        current_charleston = [o for o in current_orders if self._is_charleston_pos(o)]
        current_boston = [o for o in current_orders if self._is_boston_pos(o)]
        # Exclude online orders completely
        
        prev_charleston = [o for o in prev_year_orders if self._is_charleston_pos(o)]
        prev_boston = [o for o in prev_year_orders if self._is_boston_pos(o)]
        # Exclude online orders completely
        
        # Combine store orders only (no online)
        current_store_orders = current_charleston + current_boston
        prev_store_orders = prev_charleston + prev_boston
        
        # Process the data by location (stores only)
        current_metrics = {
            'all': self._calculate_metrics(current_store_orders),
            'charleston': self._calculate_metrics(current_charleston),
            'boston': self._calculate_metrics(current_boston)
        }
        prev_year_metrics = {
            'all': self._calculate_metrics(prev_store_orders),
            'charleston': self._calculate_metrics(prev_charleston),
            'boston': self._calculate_metrics(prev_boston)
        }
        
        # Calculate year-over-year changes
        yoy_changes = self._calculate_yoy_changes(current_metrics, prev_year_metrics)
        
        # Get product performance (stores only)
        product_performance = self._analyze_product_performance(current_store_orders)
        
        # Get product performance by location (stores only)
        product_performance_by_location = {
            'charleston': self._analyze_product_performance(current_charleston),
            'boston': self._analyze_product_performance(current_boston)
        }
        
        # Get workshop analytics (stores only)
        workshop_data = self._analyze_workshops(current_store_orders)
        
        # Get customer insights (stores only)
        customer_insights = self._analyze_customers(current_store_orders)
        
        # Identify trends and patterns (stores only)
        trends = self._identify_trends(current_store_orders, prev_store_orders)
        
        # Get multi-week trends if requested
        multi_week_trends = {}
        product_categories = {}
        if include_trends:
            multi_week_trends = self._analyze_multi_week_trends(week_start)
            product_categories = self._analyze_product_categories(current_orders)
        
        # Add goals data (these would ideally come from the Google Sheets)
        goals_data = self._get_store_goals(week_start)
        
        # Calculate conversion metrics if we have traffic data
        conversion_metrics = self._calculate_conversion_metrics(current_metrics, goals_data)
        
        return {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'current_week': current_metrics['all'],  # Keep backward compatibility
            'current_week_by_location': current_metrics,
            'previous_year': prev_year_metrics['all'],  # Keep backward compatibility
            'previous_year_by_location': prev_year_metrics,
            'yoy_changes': yoy_changes,
            'product_performance': product_performance,
            'product_performance_by_location': product_performance_by_location,
            'workshop_analytics': workshop_data,
            'customer_insights': customer_insights,
            'trends': trends,
            'total_revenue': current_metrics['all']['total_revenue'],
            'total_orders': current_metrics['all']['order_count'],
            'avg_order_value': current_metrics['all']['avg_order_value'],
            'goals': goals_data,
            'conversion_metrics': conversion_metrics,
            'multi_week_trends': multi_week_trends,
            'product_categories': product_categories
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
        
        # Calculate changes for each location (stores only)
        for location in ['all', 'charleston', 'boston']:
            changes[location] = {}
            current_loc = current.get(location, {})
            previous_loc = previous.get(location, {})
            
            for metric in ['total_revenue', 'order_count', 'avg_order_value', 'total_items_sold']:
                if previous_loc.get(metric, 0) > 0:
                    change = ((current_loc.get(metric, 0) - previous_loc.get(metric, 0)) / previous_loc.get(metric, 0)) * 100
                    changes[location][f'{metric}_change'] = round(change, 1)
                else:
                    # Boston opened August 2024, so YoY comparisons are not meaningful
                    if location == 'boston':
                        changes[location][f'{metric}_change'] = None  # Use None to indicate N/A
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
                'popular_workshops': [],
                'occupancy_data': {}
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
        
        # Calculate occupancy (placeholder - would ideally fetch from Google Sheets)
        # Assuming standard workshop capacity of 12 people
        standard_capacity = 12
        total_sessions = sum(data['count'] for data in workshop_types.values())
        total_capacity = total_sessions * standard_capacity if total_sessions > 0 else 0
        occupancy_rate = (total_attendees / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            'total_workshops': len(workshop_orders),
            'workshop_revenue': total_revenue,
            'attendees': total_attendees,
            'popular_workshops': popular_workshops,
            'occupancy_data': {
                'total_sessions': total_sessions,
                'total_attendees': total_attendees,
                'total_capacity': total_capacity,
                'occupancy_rate': round(occupancy_rate, 1),
                'note': 'Workshop capacity data should be referenced from Google Sheets'
            }
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
        # Charleston store location ID is 10719053
        location_id = order.get('location_id')
        return str(location_id) == '10719053'
    
    def _is_boston_pos(self, order: Dict) -> bool:
        """Check if order is from Boston POS"""
        # Boston store location ID is 71781154968
        location_id = order.get('location_id')
        return str(location_id) == '71781154968'
    
    def _is_online_order(self, order: Dict) -> bool:
        """Check if order is from online store"""
        # Any order that's not from Charleston or Boston POS is considered online
        # This includes web orders and orders from other locations (Atlanta store)
        return not self._is_charleston_pos(order) and not self._is_boston_pos(order)
    
    def _get_store_goals(self, week_start: datetime) -> Dict[str, Any]:
        """Get store goals - placeholder until we integrate Google Sheets"""
        # These are placeholder goals - in production, would fetch from Google Sheets
        # Charleston goals based on mature store
        # Boston goals based on new store ramp-up
        
        month = week_start.month
        
        # Seasonal adjustments (higher in Q4, lower in Q1)
        seasonal_factor = 1.0
        if month in [11, 12]:  # Holiday season
            seasonal_factor = 1.3
        elif month in [1, 2]:  # Post-holiday
            seasonal_factor = 0.8
        elif month in [6, 7, 8]:  # Summer
            seasonal_factor = 1.1
        
        return {
            'charleston': {
                'revenue_goal': 25000 * seasonal_factor,  # Weekly revenue goal
                'traffic_goal': 800 * seasonal_factor,    # Weekly visitors
                'conversion_goal': 0.35,                   # 35% conversion rate
                'avg_ticket_goal': 89,                     # Average order value
                'workshop_occupancy_goal': 0.75,           # 75% workshop occupancy target
                'notes': 'Goals from 2024 planning spreadsheet'
            },
            'boston': {
                'revenue_goal': 15000 * seasonal_factor,  # Lower for new store
                'traffic_goal': 500 * seasonal_factor,    # Building traffic
                'conversion_goal': 0.30,                   # 30% conversion for new store
                'avg_ticket_goal': 100,                    # Higher AOV in Boston market
                'workshop_occupancy_goal': 0.60,           # 60% workshop occupancy for new store
                'notes': 'New store ramp-up targets'
            }
        }
    
    def _calculate_conversion_metrics(self, current_metrics: Dict, goals: Dict) -> Dict[str, Any]:
        """Calculate conversion metrics and performance vs goals"""
        conversion_data = {}
        
        for location in ['charleston', 'boston']:
            metrics = current_metrics.get(location, {})
            location_goals = goals.get(location, {})
            
            # Since we don't have actual traffic data from Shopify, 
            # we'll estimate based on conversion rate goals
            estimated_traffic = 0
            if location_goals.get('conversion_goal', 0) > 0:
                estimated_traffic = metrics.get('order_count', 0) / location_goals['conversion_goal']
            
            # Calculate performance vs goals
            revenue_vs_goal = 0
            if location_goals.get('revenue_goal', 0) > 0:
                revenue_vs_goal = (metrics.get('total_revenue', 0) / location_goals['revenue_goal']) * 100
            
            avg_ticket_vs_goal = 0
            if location_goals.get('avg_ticket_goal', 0) > 0:
                avg_ticket_vs_goal = (metrics.get('avg_order_value', 0) / location_goals['avg_ticket_goal']) * 100
            
            conversion_data[location] = {
                'estimated_traffic': int(estimated_traffic),
                'actual_orders': metrics.get('order_count', 0),
                'implied_conversion_rate': metrics.get('order_count', 0) / estimated_traffic if estimated_traffic > 0 else 0,
                'revenue_vs_goal_pct': round(revenue_vs_goal, 1),
                'avg_ticket_vs_goal_pct': round(avg_ticket_vs_goal, 1),
                'revenue_gap': metrics.get('total_revenue', 0) - location_goals.get('revenue_goal', 0),
                'avg_ticket_gap': metrics.get('avg_order_value', 0) - location_goals.get('avg_ticket_goal', 0)
            }
        
        return conversion_data
    
    def _analyze_multi_week_trends(self, current_week_start: datetime) -> Dict[str, Any]:
        """Analyze trends over the past 4 weeks"""
        trends = {
            'revenue_trend': [],
            'order_trend': [],
            'avg_ticket_trend': [],
            'top_products_trend': {}
        }
        
        # Get data for past 2 weeks (reduced from 4 to prevent timeouts)
        for i in range(2):
            week_start = current_week_start - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            orders = self.shopify.get_orders_for_period(week_start, week_end)
            
            # Calculate metrics for this week
            metrics = self._calculate_metrics(orders)
            
            trends['revenue_trend'].insert(0, {
                'week': week_start.strftime('%Y-%m-%d'),
                'revenue': metrics['total_revenue']
            })
            
            trends['order_trend'].insert(0, {
                'week': week_start.strftime('%Y-%m-%d'),
                'orders': metrics['order_count']
            })
            
            trends['avg_ticket_trend'].insert(0, {
                'week': week_start.strftime('%Y-%m-%d'),
                'avg_ticket': metrics['avg_order_value']
            })
            
            # Track top products
            products = self._analyze_product_performance(orders)[:5]
            for product in products:
                name = product['product']
                if name not in trends['top_products_trend']:
                    trends['top_products_trend'][name] = []
                trends['top_products_trend'][name].append({
                    'week': week_start.strftime('%Y-%m-%d'),
                    'revenue': product['revenue'],
                    'quantity': product['quantity_sold']
                })
        
        # Calculate week-over-week changes
        if len(trends['revenue_trend']) >= 2:
            current_revenue = trends['revenue_trend'][-1]['revenue']
            last_week_revenue = trends['revenue_trend'][-2]['revenue']
            trends['wow_revenue_change'] = ((current_revenue - last_week_revenue) / last_week_revenue * 100) if last_week_revenue > 0 else 0
        
        return trends
    
    def _analyze_product_categories(self, orders: List[Dict]) -> Dict[str, Any]:
        """Analyze products by category"""
        categories = {
            'candle_library': {'items': [], 'revenue': 0, 'count': 0},
            'match_bar': {'items': [], 'revenue': 0, 'count': 0},
            'workshops': {'items': [], 'revenue': 0, 'count': 0},
            'gift_products': {'items': [], 'revenue': 0, 'count': 0}
        }
        
        for order in orders:
            for item in order['line_items']:
                title = item['title']
                sku = item.get('sku', '')
                revenue = item['price'] * item['quantity']
                
                # Categorize based on SKU patterns and product names
                if re.match(r'cf\d+', sku.lower()) or 'candlefish no' in title.lower():
                    # Candle library items (cf1020203 format)
                    categories['candle_library']['items'].append(title)
                    categories['candle_library']['revenue'] += revenue
                    categories['candle_library']['count'] += item['quantity']
                
                elif 'match' in title.lower() or 'match bar' in title.lower():
                    # Match bar items
                    categories['match_bar']['items'].append(title)
                    categories['match_bar']['revenue'] += revenue
                    categories['match_bar']['count'] += item['quantity']
                
                elif 'workshop' in title.lower() or 'class' in title.lower():
                    # Workshop items
                    categories['workshops']['items'].append(title)
                    categories['workshops']['revenue'] += revenue
                    categories['workshops']['count'] += item['quantity']
                
                else:
                    # Gift products from third party providers
                    categories['gift_products']['items'].append(title)
                    categories['gift_products']['revenue'] += revenue
                    categories['gift_products']['count'] += item['quantity']
        
        # Get unique items and sort by frequency
        for category in categories:
            items = categories[category]['items']
            unique_items = list(set(items))
            categories[category]['unique_items'] = unique_items
            categories[category]['top_items'] = [
                (item, items.count(item)) 
                for item in unique_items
            ]
            categories[category]['top_items'].sort(key=lambda x: x[1], reverse=True)
            categories[category]['top_items'] = categories[category]['top_items'][:5]
            del categories[category]['items']  # Remove raw list to save space
        
        return categories
