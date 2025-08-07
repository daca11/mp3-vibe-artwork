"""
Bulk operations routes for MP3 Artwork Manager
"""
from flask import Blueprint, jsonify, request, current_app
from app.services.bulk_operations import BulkOperationsService
from app.services.task_manager import get_task_manager

bp = Blueprint('bulk', __name__, url_prefix='/api')


@bp.route('/bulk/process', methods=['POST'])
def bulk_process():
    """Start bulk processing of multiple files"""
    try:
        data = request.get_json()
        if not data or 'file_ids' not in data:
            return jsonify({'error': 'No file IDs provided'}), 400
        
        file_ids = data['file_ids']
        if not file_ids:
            return jsonify({'error': 'Empty file ID list'}), 400
        
        background = data.get('background', True)
        
        bulk_service = BulkOperationsService()
        
        if background:
            # Start as background task
            task_id = bulk_service.start_bulk_processing_task(file_ids)
            
            if task_id:
                return jsonify({
                    'message': 'Bulk processing started',
                    'task_id': task_id,
                    'file_count': len(file_ids),
                    'background': True
                }), 202
            else:
                return jsonify({'error': 'Failed to start bulk processing task'}), 500
        else:
            # Process immediately
            result = bulk_service.bulk_process_files(file_ids)
            return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Bulk processing failed: {str(e)}")
        return jsonify({'error': 'Bulk processing failed'}), 500


@bp.route('/bulk/artwork-select', methods=['POST'])
def bulk_artwork_select():
    """Apply artwork selections to multiple files"""
    try:
        data = request.get_json()
        if not data or 'selections' not in data:
            return jsonify({'error': 'No selections provided'}), 400
        
        selections = data['selections']
        if not selections:
            return jsonify({'error': 'Empty selections list'}), 400
        
        bulk_service = BulkOperationsService()
        result = bulk_service.bulk_apply_artwork_selection(selections)
        
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Bulk artwork selection failed: {str(e)}")
        return jsonify({'error': 'Bulk artwork selection failed'}), 500


@bp.route('/bulk/output', methods=['POST'])
def bulk_output():
    """Generate output files for multiple files"""
    try:
        data = request.get_json()
        if not data or 'file_ids' not in data:
            return jsonify({'error': 'No file IDs provided'}), 400
        
        file_ids = data['file_ids']
        if not file_ids:
            return jsonify({'error': 'Empty file ID list'}), 400
        
        create_zip = data.get('create_zip', True)
        background = data.get('background', True)
        
        bulk_service = BulkOperationsService()
        
        if background:
            # Start as background task
            task_id = bulk_service.start_bulk_output_task(file_ids, create_zip)
            
            if task_id:
                return jsonify({
                    'message': 'Bulk output generation started',
                    'task_id': task_id,
                    'file_count': len(file_ids),
                    'create_zip': create_zip,
                    'background': True
                }), 202
            else:
                return jsonify({'error': 'Failed to start bulk output task'}), 500
        else:
            # Process immediately
            result = bulk_service.bulk_generate_output(file_ids, create_zip)
            return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Bulk output generation failed: {str(e)}")
        return jsonify({'error': 'Bulk output generation failed'}), 500


@bp.route('/bulk/strategies', methods=['GET'])
def get_artwork_strategies():
    """Get available artwork selection strategies"""
    strategies = [
        {
            'id': 'prefer_embedded',
            'name': 'Prefer Embedded',
            'description': 'Prefer artwork embedded in MP3 files, fall back to MusicBrainz'
        },
        {
            'id': 'prefer_musicbrainz',
            'name': 'Prefer MusicBrainz',
            'description': 'Prefer artwork from MusicBrainz, fall back to embedded'
        },
        {
            'id': 'highest_resolution',
            'name': 'Highest Resolution',
            'description': 'Select artwork with the highest resolution'
        },
        {
            'id': 'smallest_file',
            'name': 'Smallest File',
            'description': 'Select artwork with the smallest file size'
        }
    ]
    
    return jsonify({'strategies': strategies}), 200


@bp.route('/bulk/apply-strategy', methods=['POST'])
def apply_strategy_to_files():
    """Apply a selection strategy to multiple files"""
    try:
        data = request.get_json()
        if not data or 'file_ids' not in data or 'strategy' not in data:
            return jsonify({'error': 'Missing file_ids or strategy'}), 400
        
        file_ids = data['file_ids']
        strategy = data['strategy']
        
        if not file_ids:
            return jsonify({'error': 'Empty file ID list'}), 400
        
        # Convert to selections format
        selections = [{'file_id': file_id, 'strategy': strategy} for file_id in file_ids]
        
        bulk_service = BulkOperationsService()
        result = bulk_service.bulk_apply_artwork_selection(selections)
        
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Strategy application failed: {str(e)}")
        return jsonify({'error': 'Strategy application failed'}), 500


@bp.route('/bulk/stats', methods=['GET'])
def get_bulk_stats():
    """Get bulk operation statistics"""
    try:
        from app.models.file_queue import get_queue
        
        queue = get_queue()
        files = queue.get_all_files()
        
        stats = {
            'total_files': len(files),
            'files_with_artwork': 0,
            'files_with_selection': 0,
            'files_ready_for_output': 0,
            'files_with_output': 0,
            'artwork_sources': {
                'embedded': 0,
                'musicbrainz': 0
            }
        }
        
        for file_obj in files:
            if file_obj.artwork_options:
                stats['files_with_artwork'] += 1
                
                # Count artwork sources
                for artwork in file_obj.artwork_options:
                    source = artwork.get('source', 'unknown')
                    if source in stats['artwork_sources']:
                        stats['artwork_sources'][source] += 1
            
            if file_obj.selected_artwork:
                stats['files_with_selection'] += 1
                
                if not file_obj.output_path:
                    stats['files_ready_for_output'] += 1
            
            if file_obj.output_path:
                stats['files_with_output'] += 1
        
        # Get task manager stats
        task_manager = get_task_manager()
        task_stats = task_manager.get_stats()
        
        stats['task_stats'] = task_stats
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get bulk stats: {str(e)}")
        return jsonify({'error': 'Failed to get statistics'}), 500
