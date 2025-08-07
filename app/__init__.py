from flask import Flask
from flask_cors import CORS
import logging
import os

def create_app(config_name='default'):
    """Application factory function"""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    CORS(app)
    
    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = logging.FileHandler('logs/mp3_artwork_manager.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('MP3 Artwork Manager startup')
    
    # Register blueprints
    from app.routes import upload, processing, artwork, output, tasks, bulk
    app.register_blueprint(upload.bp)
    app.register_blueprint(processing.bp)
    app.register_blueprint(artwork.bp)
    app.register_blueprint(output.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(bulk.bp)
    
    # Register main routes
    from app.routes import main
    app.register_blueprint(main.bp)
    
    return app
