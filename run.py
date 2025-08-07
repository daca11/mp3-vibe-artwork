#!/usr/bin/env python3
"""
MP3 Artwork Manager
Main application entry point
"""

import os
from app import create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
