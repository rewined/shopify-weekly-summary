#!/usr/bin/env python3
"""Manually trigger Sophie to check for email replies right now"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for proper imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from src.reply_processor import ReplyProcessor
    
    print(f"🔍 Checking for email replies at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    processor = ReplyProcessor()
    replies = processor.process_replies()
    
    if replies:
        print(f"✅ Found and processed {len(replies)} email replies:")
        for reply in replies:
            sender = reply['sender']
            response_sent = reply.get('response_sent', False)
            status = "✅ Response sent" if response_sent else "❌ Response failed"
            print(f"  - {sender}: {status}")
    else:
        print("📭 No new email replies found")
        
    print("\n💡 Note: Email replies are normally processed every hour automatically")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure you have the required environment variables:")
    print("  IMAP_SERVER, IMAP_USERNAME, IMAP_PASSWORD")
    print("  MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD") 
    print("  ANTHROPIC_API_KEY")