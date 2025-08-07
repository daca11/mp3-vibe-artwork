from flask import Blueprint, request, jsonify, current_app
import os
from werkzeug.utils import secure_filename
from app.utils.validation import validate_mp3_file, get_file_info, safe_filename
from app.models.file_queue import get_queue

bp = Blueprint('upload', __name__, url_prefix='/api')


@bp.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads"""
    try:
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400
        
        queue = get_queue()
        uploaded_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
            
            # Validate the file
            is_valid, error_message = validate_mp3_file(file)
            if not is_valid:
                errors.append(error_message)
                continue
            
            try:
                # Get file info
                file_info = get_file_info(file)
                
                # Use safe_filename to preserve original name exactly
                safe_name = safe_filename(file.filename)
                
                # Create unique filename to avoid conflicts
                base_name, ext = os.path.splitext(safe_name)
                filename = f"{base_name}_{len(uploaded_files)}{ext}"
                
                # Save file to upload directory
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)
                
                # Add to queue
                queued_file = queue.add_file(
                    filename=file.filename,  # Preserve original filename
                    file_path=upload_path,
                    size=file_info['size'],
                    mime_type=file_info['mime_type']
                )
                
                uploaded_files.append({
                    'id': queued_file.id,
                    'filename': queued_file.filename,
                    'size': queued_file.size,
                    'status': queued_file.status.value
                })
                
                current_app.logger.info(f"Successfully uploaded file: {file.filename}")
                
            except Exception as e:
                error_msg = f"Failed to upload {file.filename}: {str(e)}"
                errors.append(error_msg)
                current_app.logger.error(error_msg)
        
        # Prepare response
        response = {
            'uploaded_files': uploaded_files,
            'total_uploaded': len(uploaded_files),
            'total_errors': len(errors)
        }
        
        if errors:
            response['errors'] = errors
        
        if uploaded_files:
            return jsonify(response), 200
        else:
            return jsonify({
                'error': 'No files were uploaded successfully',
                'errors': errors
            }), 400
    
    except Exception as e:
        current_app.logger.error(f"Upload endpoint error: {str(e)}")
        return jsonify({'error': 'Internal server error during upload'}), 500


@bp.route('/upload/status', methods=['GET'])
def upload_status():
    """Get upload system status"""
    queue = get_queue()
    files = queue.get_all_files()
    
    status = {
        'total_files': len(files),
        'pending': len(queue.get_files_by_status('pending')),
        'processing': len(queue.get_files_by_status('processing')),
        'completed': len(queue.get_files_by_status('completed')),
        'error': len(queue.get_files_by_status('error')),
        'max_file_size_mb': current_app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    }
    
    return jsonify(status), 200
