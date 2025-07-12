import os
from datetime import datetime, timedelta
import shopify
from typing import Dict, List, Any


class ShopifyService:
    def __init__(self):
        self.shop_domain = os.getenv('SHOPIFY_SHOP_DOMAIN')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.api_key = os.getenv('SHOPIFY_API_KEY')
        
        if not all([self.shop_domain, self.access_token]):
            raise ValueError("Missing Shopify configuration. Please check environment variables.")
        
        self._init_session()
    
    def _init_session(self):
        # Use the latest stable version available
        shopify.ShopifyResource.set_site(
            f"https://{self.shop_domain}/admin/api/2023-07"
        )
        shopify.ShopifyResource.set_headers({
            'X-Shopify-Access-Token': self.access_token
        })
    
    def get_orders_for_period(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        try:
            orders = []
            
            # Format dates for Shopify API
            start_str = start_date.strftime('%Y-%m-%dT00:00:00-00:00')
            end_str = end_date.strftime('%Y-%m-%dT23:59:59-00:00')
            
            print(f"Fetching orders from {start_str} to {end_str}")
            
            # Fetch orders with cursor-based pagination
            params = {
                'created_at_min': start_str,
                'created_at_max': end_str,
                'status': 'any',
                'limit': 250
            }
            
            # Just fetch orders without pagination for now
            # The ShopifyAPI library doesn't support cursor pagination properly
            batch = shopify.Order.find(**params)
            
            if batch:
                for order in batch:
                    order_data = {
                        'id': order.id,
                        'created_at': order.created_at,
                        'total_price': float(order.total_price),
                        'subtotal_price': float(order.subtotal_price),
                        'total_tax': float(order.total_tax),
                        'customer_email': order.email,
                        'customer_name': f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "Guest",
                        'line_items': [],
                        'tags': order.tags.split(', ') if order.tags else [],
                        'note': order.note,
                        'financial_status': order.financial_status
                    }
                    
                    for item in order.line_items:
                        order_data['line_items'].append({
                            'title': item.title,
                            'variant_title': item.variant_title,
                            'quantity': item.quantity,
                            'price': float(item.price),
                            'sku': item.sku,
                            'product_id': item.product_id
                        })
                    
                    orders.append(order_data)
            
            print(f"Total orders fetched: {len(orders)}")
            return orders
            
        except Exception as e:
            print(f"Error fetching orders: {str(e)}")
            return []
    
    def get_products(self) -> List[Dict]:
        try:
            products = []
            params = {'limit': 250}
            
            # Just fetch products without pagination for now
            batch = shopify.Product.find(**params)
            
            if batch:
                for product in batch:
                    product_data = {
                        'id': product.id,
                        'title': product.title,
                        'product_type': product.product_type,
                        'vendor': product.vendor,
                        'tags': product.tags.split(', ') if product.tags else [],
                        'variants': []
                    }
                    
                    for variant in product.variants:
                        product_data['variants'].append({
                            'id': variant.id,
                            'title': variant.title,
                            'price': float(variant.price),
                            'sku': variant.sku,
                            'inventory_quantity': variant.inventory_quantity
                        })
                    
                    products.append(product_data)
            
            return products
            
        except Exception as e:
            print(f"Error fetching products: {str(e)}")
            return []
    
    def get_customers_count(self) -> int:
        try:
            count = shopify.Customer.count()
            return count
        except Exception as e:
            print(f"Error fetching customer count: {str(e)}")
            return 0
    
    def get_workshop_orders(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get orders that are tagged as workshops or have workshop-related products
        """
        orders = self.get_orders_for_period(start_date, end_date)
        workshop_orders = []
        
        workshop_keywords = ['workshop', 'class', 'lesson', 'tutorial', 'session']
        
        for order in orders:
            is_workshop = False
            
            # Check order tags
            for tag in order.get('tags', []):
                if any(keyword in tag.lower() for keyword in workshop_keywords):
                    is_workshop = True
                    break
            
            # Check product titles
            if not is_workshop:
                for item in order.get('line_items', []):
                    if any(keyword in item['title'].lower() for keyword in workshop_keywords):
                        is_workshop = True
                        break
            
            # Check order notes
            if not is_workshop and order.get('note'):
                if any(keyword in order['note'].lower() for keyword in workshop_keywords):
                    is_workshop = True
            
            if is_workshop:
                workshop_orders.append(order)
        
        return workshop_orders
    
    def get_inventory_levels(self) -> Dict[str, Any]:
        """
        Get current inventory levels for all products
        """
        try:
            inventory = {}
            products = self.get_products()
            
            total_value = 0
            low_stock_items = []
            out_of_stock_items = []
            
            for product in products:
                for variant in product['variants']:
                    quantity = variant.get('inventory_quantity', 0)
                    price = variant.get('price', 0)
                    value = quantity * price
                    total_value += value
                    
                    item_info = {
                        'product': product['title'],
                        'variant': variant['title'],
                        'sku': variant['sku'],
                        'quantity': quantity,
                        'value': value
                    }
                    
                    if quantity == 0:
                        out_of_stock_items.append(item_info)
                    elif quantity < 10:  # Configurable threshold
                        low_stock_items.append(item_info)
            
            inventory['total_value'] = total_value
            inventory['low_stock_items'] = low_stock_items
            inventory['out_of_stock_items'] = out_of_stock_items
            inventory['total_skus'] = sum(len(p['variants']) for p in products)
            
            return inventory
            
        except Exception as e:
            print(f"Error fetching inventory: {str(e)}")
            return {}
    
    def close_session(self):
        """Clean up Shopify session"""
        shopify.ShopifyResource.clear_session()