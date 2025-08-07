import os
from pathlib import Path

class Config:
    """Base configuration class"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # File handling settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = 'uploads'
    TEMP_FOLDER = 'temp'
    OUTPUT_FOLDER = 'output'
    
    # Artwork optimization settings
    MAX_ARTWORK_WIDTH = 500
    MAX_ARTWORK_HEIGHT = 500
    MAX_ARTWORK_SIZE = 500 * 1024  # 500KB
    ALLOWED_ARTWORK_FORMATS = ['JPEG', 'PNG']
    
    # MusicBrainz API settings
    MUSICBRAINZ_RATE_LIMIT = 1.0  # seconds between requests
    MUSICBRAINZ_TIMEOUT = 10  # seconds
    MUSICBRAINZ_USER_AGENT = 'MP3ArtworkManager/1.0 (contact@example.com)'
    
    # Processing settings
    MAX_CONCURRENT_PROCESSES = 10
    PROCESSING_TIMEOUT = 30  # seconds per file
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        # Create necessary directories
        for folder in [Config.UPLOAD_FOLDER, Config.TEMP_FOLDER, Config.OUTPUT_FOLDER]:
            Path(folder).mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
