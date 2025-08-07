"""
Task management routes for MP3 Artwork Manager
"""
from flask import Blueprint, jsonify, request, current_app
from app.services.task_manager import get_task_manager

bp = Blueprint('tasks', __name__, url_prefix='/api')


@bp.route('/tasks', methods=['GET'])
def get_all_tasks():
    """Get all tasks"""
    try:
        task_manager = get_task_manager()
        tasks = task_manager.get_all_tasks()
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t['created_at'], reverse=True)
        
        return jsonify({
            'tasks': tasks,
            'total': len(tasks)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get tasks: {str(e)}")
        return jsonify({'error': 'Failed to get tasks'}), 500


@bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of a specific task"""
    try:
        task_manager = get_task_manager()
        task_status = task_manager.get_task_status(task_id)
        
        if not task_status:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(task_status), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get task status: {str(e)}")
        return jsonify({'error': 'Failed to get task status'}), 500


@bp.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """Cancel a task"""
    try:
        task_manager = get_task_manager()
        
        if task_manager.cancel_task(task_id):
            return jsonify({'message': 'Task cancelled successfully'}), 200
        else:
            return jsonify({'error': 'Task not found or cannot be cancelled'}), 400
        
    except Exception as e:
        current_app.logger.error(f"Failed to cancel task: {str(e)}")
        return jsonify({'error': 'Failed to cancel task'}), 500


@bp.route('/tasks/stats', methods=['GET'])
def get_task_stats():
    """Get task manager statistics"""
    try:
        task_manager = get_task_manager()
        stats = task_manager.get_stats()
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get task stats: {str(e)}")
        return jsonify({'error': 'Failed to get task stats'}), 500


@bp.route('/tasks/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """Clean up old completed tasks"""
    try:
        data = request.get_json() or {}
        max_age_hours = data.get('max_age_hours', 24)
        
        task_manager = get_task_manager()
        cleaned_count = task_manager.cleanup_old_tasks(max_age_hours)
        
        return jsonify({
            'message': f'Cleaned up {cleaned_count} old tasks',
            'cleaned_count': cleaned_count
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to cleanup tasks: {str(e)}")
        return jsonify({'error': 'Failed to cleanup tasks'}), 500
