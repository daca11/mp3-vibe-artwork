#!/usr/bin/env python3
"""
WSGI Entry Point
Production WSGI server entry point for MP3 Artwork Manager.
"""

import os
from app import create_app

# Get configuration from environment
config_name = os.environ.get('FLASK_CONFIG') or 'production'

# Create application with appropriate configuration
application = create_app(config_name)

if __name__ == "__main__":
    application.run() 