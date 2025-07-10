import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from io import BytesIO
import tempfile
from typing import Dict, List, Any


class ShopifyReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        
    def _create_custom_styles(self):
        """Create custom styles for the report"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#764ba2'),
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=20,
            textColor=colors.HexColor('#667eea'),
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#718096'),
            alignment=TA_CENTER
        ))
    
    def generate_report(self, analytics_data: Dict, insights: str, output_path: str = None) -> str:
        """Generate a PDF report from analytics data"""
        if not output_path:
            os.makedirs('output', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join('output', f'shopify_weekly_report_{timestamp}.pdf')
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Title
        story.append(Paragraph(
            f"Candlefish Weekly Report",
            self.styles['CustomTitle']
        ))
        
        story.append(Paragraph(
            f"{analytics_data['week_start']} to {analytics_data['week_end']}",
            self.styles['Normal']
        ))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Key Metrics Summary
        story.append(Paragraph("Key Metrics", self.styles['SectionHeader']))
        
        metrics_data = [
            ['Total Revenue', 'Orders', 'Avg Order Value', 'Items Sold'],
            [
                f"${analytics_data['current_week']['total_revenue']:,.2f}",
                str(analytics_data['current_week']['order_count']),
                f"${analytics_data['current_week']['avg_order_value']:.2f}",
                str(analytics_data['current_week']['total_items_sold'])
            ],
            [
                f"{analytics_data['yoy_changes']['total_revenue_change']:+.1f}% YoY",
                f"{analytics_data['yoy_changes']['order_count_change']:+.1f}% YoY",
                f"{analytics_data['yoy_changes']['avg_order_value_change']:+.1f}% YoY",
                f"{analytics_data['yoy_changes']['total_items_sold_change']:+.1f}% YoY"
            ]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        metrics_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, 1), 16),
            ('FONTSIZE', (0, 2), (-1, 2), 10),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#718096')),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
        ]))
        
        story.append(metrics_table)
        story.append(Spacer(1, 0.5*inch))
        
        # Create revenue trend chart
        chart_path = self._create_revenue_chart(analytics_data)
        if chart_path:
            story.append(Paragraph("Revenue Trends", self.styles['SectionHeader']))
            story.append(Image(chart_path, width=6*inch, height=3*inch))
            story.append(Spacer(1, 0.3*inch))
        
        # Top Products
        story.append(Paragraph("Top Products", self.styles['SectionHeader']))
        
        products = analytics_data.get('product_performance', [])[:5]
        if products:
            product_data = [['Product', 'Quantity', 'Revenue', 'Orders']]
            for p in products:
                product_data.append([
                    p['product'][:40] + '...' if len(p['product']) > 40 else p['product'],
                    str(p['quantity_sold']),
                    f"${p['revenue']:,.2f}",
                    str(p['order_count'])
                ])
            
            product_table = Table(product_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1*inch])
            product_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
            ]))
            
            story.append(product_table)
        
        story.append(Spacer(1, 0.5*inch))
        
        # Workshop Analytics
        workshops = analytics_data.get('workshop_analytics', {})
        if workshops.get('attendees', 0) > 0:
            story.append(Paragraph("Workshop Analytics", self.styles['SectionHeader']))
            
            workshop_metrics = [
                ['Total Workshops', 'Total Attendees', 'Workshop Revenue'],
                [
                    str(workshops['total_workshops']),
                    str(workshops['attendees']),
                    f"${workshops['workshop_revenue']:,.2f}"
                ]
            ]
            
            workshop_table = Table(workshop_metrics, colWidths=[2*inch, 2*inch, 2*inch])
            workshop_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, 1), 16),
                ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#667eea')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
            ]))
            
            story.append(workshop_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Customer Insights
        story.append(Paragraph("Customer Insights", self.styles['SectionHeader']))
        
        customers = analytics_data.get('customer_insights', {})
        customer_data = [
            ['New Customers', 'Repeat Customers', 'Repeat Rate'],
            [
                str(customers.get('new_customers', 0)),
                str(customers.get('repeat_customers', 0)),
                f"{(customers.get('repeat_customers', 0) / max(customers.get('new_customers', 0) + customers.get('repeat_customers', 0), 1) * 100):.1f}%"
            ]
        ]
        
        customer_table = Table(customer_data, colWidths=[2*inch, 2*inch, 2*inch])
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, 1), 16),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#667eea')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
        ]))
        
        story.append(customer_table)
        
        # Trends and Insights
        if analytics_data.get('trends'):
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph("Key Trends", self.styles['SectionHeader']))
            
            for trend in analytics_data['trends']:
                story.append(Paragraph(f"• {trend}", self.styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        
        # Clean up temporary chart file
        if chart_path and os.path.exists(chart_path):
            os.remove(chart_path)
        
        return output_path
    
    def _create_revenue_chart(self, analytics_data: Dict) -> str:
        """Create a revenue comparison chart"""
        try:
            # Set style
            plt.style.use('seaborn-v0_8-whitegrid')
            fig, ax = plt.subplots(figsize=(8, 4))
            
            # Data for chart
            categories = ['Revenue', 'Orders', 'AOV', 'Items']
            current_values = [
                analytics_data['current_week']['total_revenue'],
                analytics_data['current_week']['order_count'],
                analytics_data['current_week']['avg_order_value'],
                analytics_data['current_week']['total_items_sold']
            ]
            
            previous_values = [
                analytics_data['previous_year']['total_revenue'],
                analytics_data['previous_year']['order_count'],
                analytics_data['previous_year']['avg_order_value'],
                analytics_data['previous_year']['total_items_sold']
            ]
            
            # Normalize values for comparison
            max_vals = [max(c, p) if max(c, p) > 0 else 1 for c, p in zip(current_values, previous_values)]
            current_norm = [c/m * 100 for c, m in zip(current_values, max_vals)]
            previous_norm = [p/m * 100 for p, m in zip(previous_values, max_vals)]
            
            x = range(len(categories))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], current_norm, width, label='This Year', color='#667eea')
            ax.bar([i + width/2 for i in x], previous_norm, width, label='Last Year', color='#e2e8f0')
            
            ax.set_ylabel('Relative Performance (%)')
            ax.set_title('Year-over-Year Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(categories)
            ax.legend()
            
            # Add percentage change labels
            for i, (c, p) in enumerate(zip(current_values, previous_values)):
                if p > 0:
                    change = ((c - p) / p) * 100
                    ax.text(i, max(current_norm[i], previous_norm[i]) + 5, 
                           f'{change:+.1f}%', ha='center', fontsize=10, color='#718096')
            
            plt.tight_layout()
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            plt.savefig(temp_file.name, dpi=150, bbox_inches='tight')
            plt.close()
            
            return temp_file.name
            
        except Exception as e:
            print(f"Error creating chart: {str(e)}")
            return None