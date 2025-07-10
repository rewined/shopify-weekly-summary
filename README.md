# Shopify Weekly Summary

An AI-powered analytics tool that automatically generates and emails conversational weekly reports for your Shopify store.

## Features

- 🤖 AI-powered insights using Claude
- 📧 Automated weekly email delivery
- 💬 Two-way email communication
- 📊 Comprehensive analytics and PDF reports
- 🎨 Simple web interface

## Quick Start

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env`
4. Run the application: `python app.py`

## Environment Variables

See `.env` file for required configuration. Key variables include:
- Shopify API credentials
- Email SMTP/IMAP settings
- Anthropic API key
- Scheduler configuration

## Deployment

This application is configured for deployment on Railway. The Procfile and requirements.txt are set up for automatic deployment.

## Usage

Access the web interface at the deployed URL to:
- Generate and send weekly reports manually
- Send test emails
- Process email replies
- View customer feedback

The scheduler will automatically send reports every Monday at 8 AM (configurable).

## Support

For issues or questions, check the logs or review the feedback history in the web interface.