from flask import Blueprint, jsonify, current_app
from app.models.file_queue import get_queue, FileStatus
from app.models.processing_job import process_file_async, batch_process_files
from app.services.mp3_processor import MP3ProcessingError

bp = Blueprint('processing', __name__, url_prefix='/api')


@bp.route('/queue', methods=['GET'])
def get_queue_status():
    """Get the current processing queue"""
    try:
        queue = get_queue()
        files = queue.get_all_files()
        
        # Convert files to JSON-serializable format
        queue_data = []
        for file_obj in files:
            file_data = file_obj.to_dict()
            # Add preview URLs for artwork if available
            if file_data['artwork_options']:
                for artwork in file_data['artwork_options']:
                    # TODO: Implement artwork preview URLs in Phase 6
                    artwork['preview_url'] = f"/api/artwork/{file_obj.id}/preview/{artwork['id']}"
            
            queue_data.append(file_data)
        
        # Sort by creation time (newest first)
        queue_data.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify(queue_data), 200
    
    except Exception as e:
        current_app.logger.error(f"Queue status error: {str(e)}")
        return jsonify({'error': 'Failed to get queue status'}), 500


@bp.route('/queue/<file_id>', methods=['DELETE'])
def remove_file_from_queue(file_id):
    """Remove a file from the processing queue"""
    try:
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        # Check if file is currently being processed
        if file_obj.status == FileStatus.PROCESSING:
            return jsonify({'error': 'Cannot remove file that is currently being processed'}), 400
        
        # Remove the file
        if queue.remove_file(file_id):
            current_app.logger.info(f"Removed file from queue: {file_obj.filename}")
            return jsonify({'message': 'File removed successfully'}), 200
        else:
            return jsonify({'error': 'Failed to remove file'}), 500
    
    except Exception as e:
        current_app.logger.error(f"Remove file error: {str(e)}")
        return jsonify({'error': 'Failed to remove file'}), 500


@bp.route('/process/<file_id>', methods=['POST'])
def process_file(file_id):
    """Start processing a specific file"""
    try:
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        if file_obj.status != FileStatus.PENDING:
            return jsonify({'error': f'File is not pending (current status: {file_obj.status.value})'}), 400
        
        # Start actual processing
        try:
            job_result = process_file_async(file_id)
            current_app.logger.info(f"Processing job completed for {file_obj.filename}")
            
            return jsonify({
                'message': 'Processing completed',
                'file_id': file_id,
                'status': 'completed',
                'job_result': job_result
            }), 200
            
        except MP3ProcessingError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            current_app.logger.error(f"Unexpected error processing {file_id}: {str(e)}")
            return jsonify({'error': 'Processing failed unexpectedly'}), 500
    
    except Exception as e:
        current_app.logger.error(f"Process file error: {str(e)}")
        return jsonify({'error': 'Failed to start processing'}), 500


@bp.route('/process/batch', methods=['POST'])
def process_batch():
    """Start batch processing of all pending files"""
    try:
        queue = get_queue()
        pending_files = queue.get_files_by_status(FileStatus.PENDING)
        
        if not pending_files:
            return jsonify({'message': 'No pending files to process'}), 200
        
        # Start actual batch processing
        file_ids = [f.id for f in pending_files]
        
        try:
            results = batch_process_files(file_ids)
            
            successful = sum(1 for r in results if not r.get('error'))
            failed = len(results) - successful
            
            current_app.logger.info(f"Batch processing completed: {successful} successful, {failed} failed")
            
            return jsonify({
                'message': f'Batch processing completed',
                'total_files': len(file_ids),
                'successful': successful,
                'failed': failed,
                'results': results
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"Batch processing error: {str(e)}")
            return jsonify({'error': f'Batch processing failed: {str(e)}'}), 500
    
    except Exception as e:
        current_app.logger.error(f"Batch processing error: {str(e)}")
        return jsonify({'error': 'Failed to start batch processing'}), 500


@bp.route('/status/<file_id>', methods=['GET'])
def get_file_status(file_id):
    """Get processing status of a specific file"""
    try:
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        return jsonify({
            'id': file_obj.id,
            'filename': file_obj.filename,
            'status': file_obj.status.value,
            'progress': file_obj.progress,
            'error_message': file_obj.error_message,
            'updated_at': file_obj.updated_at.isoformat()
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Get file status error: {str(e)}")
        return jsonify({'error': 'Failed to get file status'}), 500
