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
from processors.error_handler import error_handler, ErrorCategory, ErrorSeverity
import time

# Set up logging
logger = logging.getLogger(__name__)

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
    """Process uploaded files with comprehensive error handling and progress tracking"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        session_data = processing_sessions[session_id]
        if session_data['status'] == 'processing':
            return jsonify({'error': 'Already processing'}), 400
        
        # Clear any previous errors
        error_handler.clear_errors()
        
        session_data['status'] = 'processing'
        session_data['processed_files'] = 0
        session_data['current_operation'] = 'initializing'
        
        # Create output directory for this session
        try:
            output_dir = file_ops.create_output_folder(session_id)
        except Exception as e:
            error = error_handler.handle_error(
                ErrorCategory.STORAGE_ERROR,
                ErrorSeverity.CRITICAL,
                f"Failed to create output directory: {str(e)}",
                exception=e
            )
            session_data['status'] = 'failed'
            return jsonify({
                'error': error_handler.get_user_friendly_message(error),
                'details': str(e)
            }), 500
        
        results = []
        start_time = time.time()
        
        for i, file_info in enumerate(session_data['files']):
            # Check for processing control signals
            if error_handler.should_stop_processing:
                session_data['status'] = 'cancelled'
                break
            
            if session_data.get('status') == 'paused':
                while session_data.get('status') == 'paused':
                    time.sleep(1)  # Wait for resume
                if session_data.get('status') == 'cancelled':
                    break
            
            try:
                file_path = Path(file_info['file_path'])
                
                # Update progress tracking
                file_info['status'] = 'processing'
                session_data['current_file'] = i
                session_data['current_operation'] = f'processing {file_path.name}'
                
                # Estimate time remaining
                elapsed_time = time.time() - start_time
                if i > 0:
                    avg_time_per_file = elapsed_time / i
                    remaining_files = len(session_data['files']) - i
                    estimated_remaining = avg_time_per_file * remaining_files
                    session_data['estimated_time_remaining'] = round(estimated_remaining)
                
                # Check for user artwork choice
                user_choice = None
                if 'artwork_choices' in session_data and i in session_data['artwork_choices']:
                    user_choice = session_data['artwork_choices'][i]
                
                # Process the file with enhanced error handling
                if user_choice:
                    result = file_ops.process_mp3_file_with_choice(file_path, output_dir, user_choice)
                else:
                    result = file_ops.process_mp3_file(file_path, output_dir, process_artwork=True)
                
                # Handle result with error categorization
                if result['success']:
                    file_info['status'] = 'completed'
                    file_info['output_path'] = str(result['output_path'])
                    file_info['processing_steps'] = result.get('processing_steps', [])
                    
                    if result.get('warnings'):
                        file_info['warnings'] = result['warnings']
                    
                    session_data['processed_files'] += 1
                    logger.info(f"Successfully processed: {file_path}")
                else:
                    file_info['status'] = 'failed'
                    
                    # Handle errors from processing result
                    if result.get('errors'):
                        file_info['errors'] = result['errors']
                        # Log to global error handler for tracking
                        for error_msg in result['errors']:
                            error_handler.handle_error(
                                ErrorCategory.FILE_VALIDATION,
                                ErrorSeverity.HIGH,
                                error_msg,
                                file_path=file_path
                            )
                    
                    if result.get('warnings'):
                        file_info['warnings'] = result['warnings']
                    
                    logger.error(f"Failed to process: {file_path}")
                
                results.append({
                    'file': file_info['filename'],
                    'success': result['success'],
                    'errors': result.get('errors', []),
                    'warnings': result.get('warnings', [])
                })
                
            except Exception as e:
                # Handle unexpected processing errors
                error = error_handler.handle_error(
                    ErrorCategory.SYSTEM_ERROR,
                    ErrorSeverity.HIGH,
                    f"Unexpected error processing {file_info['filename']}: {str(e)}",
                    file_path=Path(file_info['file_path']),
                    exception=e
                )
                
                file_info['status'] = 'failed'
                file_info['errors'] = [error_handler.get_user_friendly_message(error)]
                
                results.append({
                    'file': file_info['filename'],
                    'success': False,
                    'errors': [error_handler.get_user_friendly_message(error)],
                    'warnings': []
                })
                
                logger.error(f"Exception processing {file_info['filename']}: {e}")
        
        # Final status update
        if session_data['status'] not in ['cancelled', 'paused']:
            if session_data['processed_files'] == len(session_data['files']):
                session_data['status'] = 'completed'
            elif session_data['processed_files'] > 0:
                session_data['status'] = 'completed_with_errors'
            else:
                session_data['status'] = 'failed'
        
        session_data['current_operation'] = 'completed'
        session_data['estimated_time_remaining'] = 0
        
        # Generate processing summary
        error_summary = error_handler.get_error_summary()
        
        processing_summary = {
            'total_files': len(session_data['files']),
            'successful': session_data['processed_files'],
            'failed': len([f for f in session_data['files'] if f.get('status') == 'failed']),
            'warnings': len([f for f in session_data['files'] if f.get('warnings')]),
            'processing_time': round(time.time() - start_time, 2),
            'error_summary': error_summary
        }
        
        return jsonify({
            'status': session_data['status'],
            'message': f'Processing completed: {session_data["processed_files"]}/{len(session_data["files"])} files successful',
            'results': results,
            'summary': processing_summary,
            'output_directory': str(output_dir) if output_dir else None
        })
        
    except Exception as e:
        logger.error(f"Critical error in processing: {e}")
        
        # Handle critical processing errors
        error_handler.handle_error(
            ErrorCategory.SYSTEM_ERROR,
            ErrorSeverity.CRITICAL,
            f"Critical processing error: {str(e)}",
            exception=e
        )
        
        if session_id in processing_sessions:
            processing_sessions[session_id]['status'] = 'failed'
            processing_sessions[session_id]['current_operation'] = 'failed'
        
        return jsonify({
            'error': 'Critical processing error occurred',
            'details': str(e),
            'error_summary': error_handler.get_error_summary()
        }), 500

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

@app.route('/api/processing-status/<session_id>', methods=['GET'])
def get_processing_status(session_id):
    """Get detailed processing status including errors and progress"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        session_data = processing_sessions[session_id]
        
        # Calculate progress
        total_files = len(session_data['files'])
        processed_files = session_data.get('processed_files', 0)
        current_file = session_data.get('current_file', 0)
        
        progress_percentage = (processed_files / total_files * 100) if total_files > 0 else 0
        
        # Get error summary
        error_summary = error_handler.get_error_summary()
        
        status = {
            'session_id': session_id,
            'status': session_data['status'],
            'total_files': total_files,
            'processed_files': processed_files,
            'current_file': current_file,
            'progress_percentage': round(progress_percentage, 2),
            'errors': error_summary,
            'should_stop': error_handler.should_stop_processing,
            'current_operation': session_data.get('current_operation', 'idle'),
            'estimated_time_remaining': session_data.get('estimated_time_remaining'),
            'files': session_data['files']
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500

@app.route('/api/processing-controls/<session_id>', methods=['POST'])
def control_processing(session_id):
    """Control processing operations (pause, resume, cancel, retry)"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        data = request.get_json()
        action = data.get('action')
        
        session_data = processing_sessions[session_id]
        
        if action == 'pause':
            session_data['status'] = 'paused'
            session_data['current_operation'] = 'paused'
            
        elif action == 'resume':
            if session_data['status'] == 'paused':
                session_data['status'] = 'processing'
                session_data['current_operation'] = 'resuming'
            
        elif action == 'cancel':
            session_data['status'] = 'cancelled'
            session_data['current_operation'] = 'cancelled'
            error_handler.should_stop_processing = True
            
        elif action == 'retry_errors':
            # Clear previous errors and reset status
            error_handler.clear_errors()
            session_data['status'] = 'uploaded'
            session_data['current_operation'] = 'ready_for_retry'
            
            # Reset failed files to uploaded status
            for file_info in session_data['files']:
                if file_info.get('status') == 'failed':
                    file_info['status'] = 'uploaded'
                    file_info['error'] = None
            
        elif action == 'clear_queue':
            session_data['files'] = []
            session_data['status'] = 'empty'
            session_data['processed_files'] = 0
            session_data['current_file'] = 0
            error_handler.clear_errors()
            
        else:
            return jsonify({'error': f'Unknown action: {action}'}), 400
        
        return jsonify({
            'success': True,
            'message': f'Processing {action} completed',
            'new_status': session_data['status']
        })
        
    except Exception as e:
        logger.error(f"Error controlling processing: {e}")
        return jsonify({'error': f'Failed to control processing: {str(e)}'}), 500

@app.route('/api/error-log/<session_id>', methods=['GET'])
def get_error_log(session_id):
    """Get detailed error log for debugging"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        error_summary = error_handler.get_error_summary()
        
        # Add user-friendly messages
        for error_dict in error_summary['recent_errors']:
            error = type('Error', (), error_dict)()  # Create object from dict
            error_dict['user_message'] = error_handler.get_user_friendly_message(error)
        
        return jsonify(error_summary)
        
    except Exception as e:
        logger.error(f"Error getting error log: {e}")
        return jsonify({'error': f'Failed to get error log: {str(e)}'}), 500

@app.route('/api/export-error-log/<session_id>', methods=['POST'])
def export_error_log(session_id):
    """Export detailed error log to file"""
    try:
        if session_id not in processing_sessions:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        from pathlib import Path
        import tempfile
        
        # Create temporary file for error log
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = Path(f.name)
        
        error_handler.export_error_log(temp_path)
        
        # Read the file content for download
        log_content = temp_path.read_text(encoding='utf-8')
        
        # Clean up temp file
        temp_path.unlink()
        
        return jsonify({
            'success': True,
            'log_content': log_content,
            'filename': f'error_log_{session_id}.txt'
        })
        
    except Exception as e:
        logger.error(f"Error exporting error log: {e}")
        return jsonify({'error': f'Failed to export error log: {str(e)}'}), 500

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