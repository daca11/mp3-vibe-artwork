#!/usr/bin/env python3
"""
MP3 Artwork Manager for Traktor 3
A web-based application for processing MP3 artwork to meet Traktor specifications.
"""

import os
import json
import uuid
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from processors.file_operations import FileOperations
from processors.file_handler import MP3FileHandler
from processors.artwork_processor import ArtworkProcessor

# Initialize Flask application
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# Create necessary directories
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(exist_ok=True)

# Initialize processors
file_ops = FileOperations(output_base_dir=app.config['OUTPUT_FOLDER'], enable_musicbrainz=True)
mp3_handler = MP3FileHandler()
artwork_processor = ArtworkProcessor()

# Store processing sessions (in production, use Redis or database)
processing_sessions = {}

def safe_filename(filename):
    """
    Create a safe filename that preserves the original name while preventing security issues.
    Only prevents directory traversal - does not sanitize special characters.
    """
    if not filename:
        return None
    
    # Remove any directory path components to prevent traversal
    # Handle both Unix (/) and Windows (\) path separators
    safe_name = os.path.basename(filename.replace('\\', '/'))
    
    # Ensure we still have a valid filename
    if not safe_name or safe_name in ('.', '..') or '/' in safe_name or '\\' in safe_name:
        return None
        
    return safe_name

@app.route('/')
def index():
    """Main application interface"""
    return render_template('index.html')

@app.route('/hello')
def hello():
    """Basic hello world route for testing"""
    return "Hello World - MP3 Artwork Manager is running!"

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files selected'}), 400
        
        # Create a session ID for this upload batch
        session_id = str(uuid.uuid4())
        session['current_session'] = session_id
        
        # Initialize session data
        processing_sessions[session_id] = {
            'files': [],
            'total_files': 0,
            'processed_files': 0,
            'status': 'uploaded'
        }
        
        uploaded_files = []
        upload_folder = Path(app.config['UPLOAD_FOLDER']) / session_id
        upload_folder.mkdir(exist_ok=True)
        
        for file in files:
            if file and file.filename:
                # Validate file type
                if not file.filename.lower().endswith(('.mp3', '.MP3')):
                    continue
                
                # Secure the filename
                filename = safe_filename(file.filename)
                if not filename:
                    continue
                
                # Save file
                file_path = upload_folder / filename
                file.save(str(file_path))
                
                # Get basic file info
                file_info = {
                    'filename': filename,
                    'original_filename': file.filename,
                    'file_path': str(file_path),
                    'status': 'uploaded',
                    'error': None
                }
                
                # Try to extract metadata
                try:
                    metadata = mp3_handler.extract_metadata(file_path)
                    file_info.update({
                        'artist': metadata.get('artist'),
                        'title': metadata.get('title'),
                        'album': metadata.get('album')
                    })
                    
                    # If metadata is missing, try filename parsing
                    if not file_info['artist'] or not file_info['title']:
                        parsed = file_ops.parse_filename_for_metadata(filename)
                        if parsed['artist']:
                            file_info['artist'] = file_info['artist'] or parsed['artist']
                        if parsed['title']:
                            file_info['title'] = file_info['title'] or parsed['title']
                except Exception as e:
                    file_info['error'] = f"Error reading metadata: {str(e)}"
                
                uploaded_files.append(file_info)
        
        if not uploaded_files:
            return jsonify({'error': 'No valid MP3 files found'}), 400
        
        # Update session
        processing_sessions[session_id]['files'] = uploaded_files
        processing_sessions[session_id]['total_files'] = len(uploaded_files)
        
        return jsonify({
            'session_id': session_id,
            'files': uploaded_files,
            'total_files': len(uploaded_files),
            'message': f'Successfully uploaded {len(uploaded_files)} MP3 files'
        })
        
    except RequestEntityTooLarge:
        return jsonify({'error': 'File too large. Maximum size is 100MB'}), 413
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/process/<session_id>', methods=['POST'])
def process_files(session_id):
    """Process uploaded files"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        session_data = processing_sessions[session_id]
        if session_data['status'] == 'processing':
            return jsonify({'error': 'Already processing'}), 400
        
        session_data['status'] = 'processing'
        session_data['processed_files'] = 0
        
        # Create output directory for this session
        output_dir = file_ops.create_output_folder(session_id)
        
        results = []
        for i, file_info in enumerate(session_data['files']):
            try:
                file_path = Path(file_info['file_path'])
                
                # Update file status
                file_info['status'] = 'processing'
                session_data['current_file'] = i
                
                # Check for user artwork choice
                user_choice = None
                if 'artwork_choices' in session_data and i in session_data['artwork_choices']:
                    user_choice = session_data['artwork_choices'][i]
                
                # Process the file with user choice if available
                if user_choice:
                    result = file_ops.process_mp3_file_with_choice(file_path, output_dir, user_choice)
                else:
                    result = file_ops.process_mp3_file(file_path, output_dir, process_artwork=True)
                
                if result['success']:
                    file_info['status'] = 'completed'
                    file_info['output_path'] = str(result['output_path'])
                    file_info['processing_info'] = {
                        'artwork_processed': result['artwork_info'].get('processing_needed', False),
                        'artwork_compliant': result['artwork_info'].get('was_compliant', False),
                        'metadata_extracted': bool(result['metadata']),
                        'filename_parsed': bool(result['parsing_info'].get('artist'))
                    }
                else:
                    file_info['status'] = 'error'
                    file_info['error'] = result['error']
                
                session_data['processed_files'] += 1
                results.append(file_info)
                
            except Exception as e:
                file_info['status'] = 'error'
                file_info['error'] = str(e)
                session_data['processed_files'] += 1
                results.append(file_info)
        
        session_data['status'] = 'completed'
        session_data['output_dir'] = str(output_dir)
        
        return jsonify({
            'session_id': session_id,
            'status': 'completed',
            'results': results,
            'processed_files': session_data['processed_files'],
            'total_files': session_data['total_files']
        })
        
    except Exception as e:
        if session_id in processing_sessions:
            processing_sessions[session_id]['status'] = 'error'
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/status/<session_id>')
def get_status(session_id):
    """Get processing status for a session"""
    if session_id not in processing_sessions:
        return jsonify({'error': 'Invalid session ID'}), 404
    
    session_data = processing_sessions[session_id]
    return jsonify({
        'session_id': session_id,
        'status': session_data['status'],
        'processed_files': session_data['processed_files'],
        'total_files': session_data['total_files'],
        'current_file': session_data.get('current_file', 0),
        'files': session_data['files']
    })

@app.route('/download/<session_id>')
def download_files(session_id):
    """Download processed files as a zip"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        session_data = processing_sessions[session_id]
        if session_data['status'] != 'completed':
            return jsonify({'error': 'Processing not completed'}), 400
        
        output_dir = Path(session_data.get('output_dir', ''))
        if not output_dir.exists():
            return jsonify({'error': 'Output directory not found'}), 404
        
        # For now, return the first processed file
        # In a full implementation, create a zip file with all processed files
        completed_files = [f for f in session_data['files'] if f['status'] == 'completed']
        if not completed_files:
            return jsonify({'error': 'No completed files to download'}), 404
        
        first_file = Path(completed_files[0]['output_path'])
        if first_file.exists():
            return send_file(str(first_file), as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/api/validate', methods=['POST'])
def validate_files():
    """Validate files without processing"""
    try:
        data = request.json
        if not data or 'files' not in data:
            return jsonify({'error': 'No files provided'}), 400
        
        results = []
        for file_info in data['files']:
            try:
                file_path = Path(file_info['path'])
                if not file_path.exists():
                    results.append({'error': 'File not found', 'valid': False})
                    continue
                
                # Validate MP3
                is_valid, error = mp3_handler.validate_mp3_file(file_path)
                
                # Get artwork info if available
                artwork_info = None
                if is_valid:
                    artwork = mp3_handler.extract_artwork(file_path)
                    if artwork:
                        artwork_valid, issues = artwork_processor.validate_artwork(artwork['data'])
                        artwork_info = {
                            'exists': True,
                            'valid': artwork_valid,
                            'issues': issues
                        }
                    else:
                        artwork_info = {'exists': False}
                
                results.append({
                    'valid': is_valid,
                    'error': error,
                    'artwork': artwork_info
                })
                
            except Exception as e:
                results.append({'error': str(e), 'valid': False})
        
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': f'Validation failed: {str(e)}'}), 500

@app.route('/api/artwork-options/<session_id>/<file_index>', methods=['GET'])
def get_artwork_options(session_id, file_index):
    """Get artwork options for a specific file"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        session_data = processing_sessions[session_id]
        file_index = int(file_index)
        
        if file_index >= len(session_data['files']):
            return jsonify({'error': 'Invalid file index'}), 404
        
        file_info = session_data['files'][file_index]
        file_path = Path(file_info['file_path'])
        
        # Extract metadata and parse filename
        metadata = mp3_handler.extract_metadata(file_path)
        parsed_info = file_ops.parse_filename_for_metadata(file_path.name) if not metadata.get('artist') else None
        
        # Get artwork options from MusicBrainz
        artwork_options = file_ops.search_artwork_online(metadata, parsed_info, return_options=True)
        
        # Get current artwork info if any
        current_artwork = mp3_handler.extract_artwork(file_path)
        current_artwork_info = None
        
        if current_artwork:
            current_artwork_info = {
                'has_artwork': True,
                'format': current_artwork['format'],
                'size_bytes': len(current_artwork['data']),
                'description': current_artwork.get('description', ''),
                'data_url': f"data:{current_artwork['format']};base64," + 
                           __import__('base64').b64encode(current_artwork['data']).decode()
            }
        
        return jsonify({
            'file_info': {
                'filename': file_info['filename'],
                'artist': metadata.get('artist') or (parsed_info.get('artist') if parsed_info else None),
                'title': metadata.get('title') or (parsed_info.get('title') if parsed_info else None),
                'album': metadata.get('album')
            },
            'current_artwork': current_artwork_info,
            'artwork_options': artwork_options
        })
        
    except Exception as e:
        logger.error(f"Error getting artwork options: {e}")
        return jsonify({'error': f'Failed to get artwork options: {str(e)}'}), 500

@app.route('/api/artwork-preview', methods=['POST'])
def preview_artwork():
    """Preview how artwork will look after processing"""
    try:
        data = request.get_json()
        artwork_url = data.get('artwork_url')
        
        if not artwork_url:
            return jsonify({'error': 'Artwork URL required'}), 400
        
        # Download the artwork
        artwork_data = file_ops.musicbrainz_client.download_artwork(artwork_url) if file_ops.musicbrainz_client else None
        
        if not artwork_data:
            return jsonify({'error': 'Failed to download artwork'}), 400
        
        # Process artwork to show compliance preview
        artwork_result = artwork_processor.process_artwork(artwork_data, force_compliance=True)
        
        if not artwork_result['is_compliant']:
            return jsonify({'error': 'Artwork could not be made compliant'}), 400
        
        # Return preview information
        preview_info = {
            'original_size_bytes': len(artwork_data),
            'processed_size_bytes': len(artwork_result['processed_data']),
            'is_compliant': artwork_result['is_compliant'],
            'was_resized': artwork_result['was_resized'],
            'was_optimized': artwork_result['was_optimized'],
            'final_dimensions': artwork_result.get('final_dimensions', {}),
            'processing_applied': artwork_result.get('processing_applied', []),
            'preview_data_url': f"data:image/jpeg;base64," + 
                              __import__('base64').b64encode(artwork_result['processed_data']).decode()
        }
        
        return jsonify(preview_info)
        
    except Exception as e:
        logger.error(f"Error previewing artwork: {e}")
        return jsonify({'error': f'Failed to preview artwork: {str(e)}'}), 500

@app.route('/api/select-artwork/<session_id>/<file_index>', methods=['POST'])
def select_artwork(session_id, file_index):
    """Select artwork for a specific file"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        session_data = processing_sessions[session_id]
        file_index = int(file_index)
        
        if file_index >= len(session_data['files']):
            return jsonify({'error': 'Invalid file index'}), 404
        
        data = request.get_json()
        artwork_url = data.get('artwork_url')
        skip_artwork = data.get('skip_artwork', False)
        
        # Store user's choice
        if 'artwork_choices' not in session_data:
            session_data['artwork_choices'] = {}
        
        session_data['artwork_choices'][file_index] = {
            'artwork_url': artwork_url,
            'skip_artwork': skip_artwork,
            'timestamp': __import__('time').time()
        }
        
        return jsonify({'success': True, 'message': 'Artwork choice saved'})
        
    except Exception as e:
        logger.error(f"Error selecting artwork: {e}")
        return jsonify({'error': f'Failed to select artwork: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Run in debug mode for development
    app.run(debug=True, host='localhost', port=5000) 