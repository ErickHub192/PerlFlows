"""
Service URLs Configuration
Centralized configuration for external service API endpoints
"""

# Airtable API
AIRTABLE_API_BASE = "https://api.airtable.com/v0"

# Dropbox API
DROPBOX_UPLOAD_URL = "https://content.dropboxapi.com/2/files/upload"
DROPBOX_API_BASE = "https://api.dropboxapi.com/2"

# GitHub API
GITHUB_API_BASE = "https://api.github.com"

# Slack API
SLACK_API_BASE = "https://slack.com/api"

# HubSpot API
HUBSPOT_API_BASE = "https://api.hubapi.com"

# Stripe API
STRIPE_API_BASE = "https://api.stripe.com/v1"

# Salesforce API (dynamic, depends on instance)
SALESFORCE_API_VERSION = "v61.0"
SALESFORCE_BASE_URL_TEMPLATE = "https://{instance}.salesforce.com"  # Replace {instance} with actual instance

# OAuth Endpoints
GOOGLE_OAUTH_BASE = "https://accounts.google.com/o/oauth2"
MICROSOFT_OAUTH_BASE = "https://login.microsoftonline.com"

# Webhook endpoints
WEBHOOK_BASE_PATH = "/api/webhooks"

# Default timeouts for HTTP requests
DEFAULT_TIMEOUT = 30.0
UPLOAD_TIMEOUT = 120.0
QUICK_TIMEOUT = 10.0