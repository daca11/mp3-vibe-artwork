from flask import Blueprint, render_template, make_response

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
    response = make_response(render_template('artwork_selection.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@bp.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy'}, 200
