"""
Output and download routes for MP3 Artwork Manager
"""
from flask import Blueprint, jsonify, request, send_file, current_app
import os
import tempfile
from app.models.file_queue import get_queue, FileStatus
from app.services.mp3_output_service import MP3OutputService, MP3OutputError

bp = Blueprint('output', __name__, url_prefix='/api')


@bp.route('/output/<file_id>', methods=['POST'])
def generate_output(file_id):
    """Generate output MP3 file with selected artwork"""
    try:
        data = request.get_json(silent=True) or {}
        output_filename = data.get('output_filename')
        
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        if not file_obj.selected_artwork:
            return jsonify({'error': 'No artwork selected for this file'}), 400
        
        output_service = MP3OutputService()
        
        # Process the file
        result = output_service.process_file_with_selection(file_obj, output_filename)
        
        # Update file object with output info
        file_obj.output_path = result['output_path']
        file_obj.output_size = result['output_size']
        file_obj.output_filename = result['output_filename']
        file_obj.status = FileStatus.COMPLETED
        
        # Save queue
        queue._save_queue()
        
        current_app.logger.info(f"Generated output for {file_obj.filename}")
        
        return jsonify({
            'message': 'Output file generated successfully',
            'file_id': file_id,
            'output_filename': result['output_filename'],
            'original_size': result['original_size'],
            'output_size': result['output_size'],
            'size_increase': result['size_increase'],
            'artwork_embedded': result['artwork_embedded'],
            'download_url': f'/api/download/{file_id}'
        }), 200
        
    except MP3OutputError as e:
        current_app.logger.error(f"Output generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in output generation: {str(e)}")
        return jsonify({'error': 'Failed to generate output file'}), 500


@bp.route('/output/batch', methods=['POST'])
def generate_batch_output():
    """Generate output files for multiple files"""
    try:
        data = request.get_json(silent=True) or {}
        file_ids = data.get('file_ids', [])
        output_pattern = data.get('output_pattern', '{filename}_with_artwork.mp3')
        create_zip = data.get('create_zip', False)
        
        if not file_ids:
            return jsonify({'error': 'No file IDs provided'}), 400
        
        queue = get_queue()
        file_objects = []
        
        # Validate all files exist and have selected artwork
        for file_id in file_ids:
            file_obj = queue.get_file(file_id)
            if not file_obj:
                return jsonify({'error': f'File not found: {file_id}'}), 404
            if not file_obj.selected_artwork:
                return jsonify({'error': f'No artwork selected for file: {file_obj.filename}'}), 400
            file_objects.append(file_obj)
        
        output_service = MP3OutputService()
        
        # Process all files
        batch_result = output_service.batch_process_files(file_objects, output_pattern)
        
        # Update file objects with output info
        output_files = []
        for result in batch_result['results']:
            if result['success']:
                file_obj = queue.get_file(result['file_id'])
                if file_obj:
                    file_obj.output_path = result['result']['output_path']
                    file_obj.output_size = result['result']['output_size']
                    file_obj.output_filename = result['result']['output_filename']
                    file_obj.status = FileStatus.COMPLETED
                    output_files.append(result['result']['output_path'])
        
        # Create ZIP archive if requested
        archive_info = None
        if create_zip and output_files:
            try:
                archive_info = output_service.create_zip_archive(output_files)
            except Exception as e:
                current_app.logger.error(f"Failed to create ZIP archive: {str(e)}")
        
        # Save queue
        queue._save_queue()
        
        response_data = {
            'message': f'Batch processing completed: {batch_result["successful"]}/{batch_result["total_files"]} successful',
            'total_files': batch_result['total_files'],
            'successful': batch_result['successful'],
            'failed': batch_result['failed'],
            'results': batch_result['results']
        }
        
        if archive_info:
            response_data['archive'] = {
                'available': True,
                'filename': archive_info['archive_name'],
                'size': archive_info['archive_size'],
                'download_url': f'/api/download/archive/{archive_info["archive_name"]}'
            }
        
        return jsonify(response_data), 200
        
    except MP3OutputError as e:
        current_app.logger.error(f"Batch output generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in batch output generation: {str(e)}")
        return jsonify({'error': 'Failed to generate batch output'}), 500


@bp.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """Download processed MP3 file"""
    try:
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        if not file_obj.output_path or not os.path.exists(file_obj.output_path):
            return jsonify({'error': 'Output file not available'}), 404
        
        # Validate the output file
        output_service = MP3OutputService()
        validation = output_service.validate_output_file(file_obj.output_path)
        
        if not validation['valid']:
            return jsonify({'error': f'Invalid output file: {validation["error"]}'}), 500
        
        # Determine download filename
        download_filename = file_obj.output_filename or os.path.basename(file_obj.output_path)
        
        current_app.logger.info(f"Serving download for {file_obj.filename} -> {download_filename}")
        
        return send_file(
            file_obj.output_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='audio/mpeg'
        )
        
    except Exception as e:
        current_app.logger.error(f"Download failed for {file_id}: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500


@bp.route('/download/archive/<filename>', methods=['GET'])
def download_archive(filename):
    """Download ZIP archive"""
    try:
        if not filename.endswith('.zip'):
            return jsonify({'error': 'Invalid archive file'}), 400
        
        archive_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        
        if not os.path.exists(archive_path):
            return jsonify({'error': 'Archive not found'}), 404
        
        current_app.logger.info(f"Serving archive download: {filename}")
        
        return send_file(
            archive_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        current_app.logger.error(f"Archive download failed for {filename}: {str(e)}")
        return jsonify({'error': 'Archive download failed'}), 500


@bp.route('/validate/<file_id>', methods=['GET'])
def validate_output(file_id):
    """Validate output file for a given file ID"""
    try:
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        if not file_obj.output_path:
            return jsonify({'error': 'No output file generated'}), 404
        
        output_service = MP3OutputService()
        validation = output_service.validate_output_file(file_obj.output_path)
        
        return jsonify({
            'file_id': file_id,
            'filename': file_obj.filename,
            'validation': validation
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Validation failed for {file_id}: {str(e)}")
        return jsonify({'error': 'Validation failed'}), 500


@bp.route('/output/status', methods=['GET'])
def output_status():
    """Get overall output status"""
    try:
        queue = get_queue()
        files = queue.get_all_files()
        
        stats = {
            'total_files': len(files),
            'ready_for_output': 0,
            'output_generated': 0,
            'pending_selection': 0,
            'no_artwork': 0
        }
        
        for file_obj in files:
            if file_obj.output_path and os.path.exists(file_obj.output_path):
                stats['output_generated'] += 1
            elif file_obj.selected_artwork:
                stats['ready_for_output'] += 1
            elif file_obj.artwork_options:
                stats['pending_selection'] += 1
            else:
                stats['no_artwork'] += 1
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get output status: {str(e)}")
        return jsonify({'error': 'Failed to get status'}), 500


@bp.route('/output/cleanup', methods=['POST'])
def cleanup_output_files():
    """Clean up output files and temporary files"""
    try:
        data = request.get_json(silent=True) or {}
        file_ids = data.get('file_ids', [])
        cleanup_all = data.get('cleanup_all', False)
        
        queue = get_queue()
        output_service = MP3OutputService()
        
        files_to_cleanup = []
        
        if cleanup_all:
            # Clean up all output files
            files = queue.get_all_files()
            for file_obj in files:
                if file_obj.output_path:
                    files_to_cleanup.append(file_obj.output_path)
                    file_obj.output_path = None
                    file_obj.output_size = None
        else:
            # Clean up specific files
            for file_id in file_ids:
                file_obj = queue.get_file(file_id)
                if file_obj and file_obj.output_path:
                    files_to_cleanup.append(file_obj.output_path)
                    file_obj.output_path = None
                    file_obj.output_size = None
        
        # Remove the files
        cleaned = output_service.cleanup_temp_files(files_to_cleanup)
        
        # Save queue
        queue._save_queue()
        
        return jsonify({
            'message': f'Cleanup completed: {cleaned} files removed',
            'files_cleaned': cleaned
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Cleanup failed: {str(e)}")
        return jsonify({'error': 'Cleanup failed'}), 500
