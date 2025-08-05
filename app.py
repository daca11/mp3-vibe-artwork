#!/usr/bin/env python3
"""
MP3 Artwork Manager for Traktor 3
A web-based application for processing MP3 artwork to meet Traktor specifications.
"""

from flask import Flask, render_template

# Initialize Flask application
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

@app.route('/')
def index():
    """Main application interface"""
    return render_template('index.html')

@app.route('/hello')
def hello():
    """Basic hello world route for testing"""
    return "Hello World - MP3 Artwork Manager is running!"

if __name__ == '__main__':
    # Run in debug mode for development
    app.run(debug=True, host='localhost', port=5000) 