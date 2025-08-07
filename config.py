#!/usr/bin/env python3
"""
Production Configuration
Configuration settings for deploying MP3 Artwork Manager to production.
"""

import os
import logging
from pathlib import Path

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    OUTPUT_FOLDER = os.environ.get('OUTPUT_FOLDER') or 'output'
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_SECURE = False  # Set to True for HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'app.log'
    
    # MusicBrainz settings
    MUSICBRAINZ_USER_AGENT = os.environ.get('MUSICBRAINZ_USER_AGENT') or 'MP3ArtworkManager/1.0'
    MUSICBRAINZ_RATE_LIMIT = float(os.environ.get('MUSICBRAINZ_RATE_LIMIT') or '1.0')  # requests per second
    
    # Performance settings
    MAX_CONCURRENT_UPLOADS = int(os.environ.get('MAX_CONCURRENT_UPLOADS') or '10')
    CLEANUP_INTERVAL = int(os.environ.get('CLEANUP_INTERVAL') or '3600')  # seconds
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config"""
        # Create necessary directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)
        
        # Set up logging
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL.upper()),
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
            handlers=[
                logging.FileHandler(Config.LOG_FILE),
                logging.StreamHandler()
            ]
        )

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    SECRET_KEY = 'dev-secret-key'
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        print('Development mode: Debug enabled')

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production security settings
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    SESSION_COOKIE_HTTPONLY = True
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    # Production performance
    MAX_CONCURRENT_UPLOADS = 50
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Ensure secret key is set
        if not app.config['SECRET_KEY']:
            raise ValueError('SECRET_KEY environment variable must be set for production')
        
        # Set up production logging
        if not app.debug and not app.testing:
            # Log to file with rotation
            import logging.handlers
            
            file_handler = logging.handlers.RotatingFileHandler(
                Config.LOG_FILE,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.WARNING)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.WARNING)
            app.logger.info('MP3 Artwork Manager startup (production)')

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    
    # Testing-specific settings
    SECRET_KEY = 'test-secret-key'
    UPLOAD_FOLDER = 'test_uploads'
    OUTPUT_FOLDER = 'test_output'
    LOG_LEVEL = 'CRITICAL'  # Suppress most logging during tests
    
    # Disable MusicBrainz for most tests
    MUSICBRAINZ_RATE_LIMIT = 0.1  # Faster for testing
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # Disable logging during tests
        logging.disable(logging.CRITICAL)

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 