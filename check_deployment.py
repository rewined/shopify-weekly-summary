#!/usr/bin/env python3
"""Check deployment requirements and environment"""

import os
import sys
from pathlib import Path

def check_deployment():
    """Check if all deployment requirements are met"""
    
    print("🔍 Railway Deployment Check")
    print("=" * 40)
    
    # Check essential files
    essential_files = [
        'app.py',
        'requirements.txt', 
        'Procfile',
        'railway.toml'
    ]
    
    print("\n📋 Essential Files:")
    all_files_present = True
    for file in essential_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING!")
            all_files_present = False
    
    # Check Python imports
    print("\n🐍 Python Import Check:")
    try:
        import flask
        print(f"  ✅ Flask {flask.__version__}")
    except ImportError:
        print("  ❌ Flask - NOT INSTALLED")
        all_files_present = False
    
    try:
        import gunicorn
        print(f"  ✅ Gunicorn {gunicorn.__version__}")
    except ImportError:
        print("  ❌ Gunicorn - NOT INSTALLED")
        all_files_present = False
    
    try:
        import anthropic
        print(f"  ✅ Anthropic {anthropic.__version__}")
    except ImportError:
        print("  ❌ Anthropic - NOT INSTALLED")
        all_files_present = False
    
    # Check environment variables (names only, not values)
    print("\n🔐 Environment Variables:")
    required_env_vars = [
        'ANTHROPIC_API_KEY',
        'SHOPIFY_SHOP_DOMAIN', 
        'SHOPIFY_ACCESS_TOKEN',
        'MAIL_USERNAME',
        'MAIL_PASSWORD',
        'IMAP_USERNAME',
        'IMAP_PASSWORD'
    ]
    
    for var in required_env_vars:
        if os.getenv(var):
            print(f"  ✅ {var}")
        else:
            print(f"  ⚠️  {var} - NOT SET (may be Railway-only)")
    
    # Check src directory
    print("\n📁 Source Code Structure:")
    src_files = [
        'src/__init__.py',
        'src/email_responder.py',
        'src/reply_processor.py',
        'src/scheduler.py',
        'src/shopify_service.py'
    ]
    
    for file in src_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING!")
            all_files_present = False
    
    # Overall status
    print("\n" + "=" * 40)
    if all_files_present:
        print("✅ DEPLOYMENT READY")
        print("All essential files and dependencies are present.")
    else:
        print("❌ DEPLOYMENT ISSUES FOUND")
        print("Please fix the missing items above.")
    
    return all_files_present

if __name__ == "__main__":
    ready = check_deployment()
    sys.exit(0 if ready else 1)