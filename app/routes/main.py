from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Main application page"""
    return render_template('index.html')

@bp.route('/queue')
def queue():
    """Processing queue page"""
    return render_template('queue.html')

@bp.route('/artwork-selection')
def artwork_selection():
    """Artwork selection page"""
    return render_template('artwork_selection.html')

@bp.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy'}, 200
