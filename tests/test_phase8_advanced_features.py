"""
Unit tests for Phase 8: Advanced Features & Polish
"""
import pytest
import tempfile
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from app import create_app
from app.services.task_manager import TaskManager, Task, TaskStatus
from app.services.bulk_operations import BulkOperationsService


@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app('testing')
    
    # Create temporary directories for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        app.config['UPLOAD_FOLDER'] = os.path.join(temp_dir, 'uploads')
        app.config['TEMP_FOLDER'] = os.path.join(temp_dir, 'temp')
        app.config['OUTPUT_FOLDER'] = os.path.join(temp_dir, 'output')
        
        os.makedirs(app.config['UPLOAD_FOLDER'])
        os.makedirs(app.config['TEMP_FOLDER'])
        os.makedirs(app.config['OUTPUT_FOLDER'])
        
        yield app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_files_with_artwork(app):
    """Create sample files with artwork for bulk operations"""
    with app.app_context():
        from app.models.file_queue import get_queue
        queue = get_queue()
        
        file_ids = []
        for i in range(3):
            # Create test files
            queued_file = queue.add_file(
                filename=f'test_song_{i}.mp3',
                file_path=f'/tmp/test_song_{i}.mp3',
                size=1024000 + i * 100000,
                mime_type='audio/mpeg'
            )
            
            # Add artwork options
            queued_file.add_artwork_option(
                source='embedded',
                image_path=f'/tmp/embedded_artwork_{i}.jpg',
                dimensions={'width': 600 + i * 100, 'height': 600 + i * 100},
                file_size=150000 + i * 10000,
                metadata={'format': 'JPEG', 'description': f'Front cover {i}'}
            )
            
            # Add MusicBrainz artwork
            queued_file.add_artwork_option(
                source='musicbrainz',
                image_path=f'/tmp/musicbrainz_artwork_{i}.jpg',
                dimensions={'width': 500 + i * 50, 'height': 500 + i * 50},
                file_size=120000 + i * 5000,
                metadata={
                    'release_title': f'Test Album {i}',
                    'release_artist': f'Test Artist {i}',
                    'primary_type': 'Front'
                }
            )
            
            file_ids.append(queued_file.id)
        
        queue._save_queue()
        
        yield file_ids
        
        # Cleanup
        for file_id in file_ids:
            queue.remove_file(file_id)


class TestTaskManager:
    """Test task manager functionality"""
    
    def test_task_manager_creation(self, app):
        """Test creating task manager"""
        with app.app_context():
            task_manager = TaskManager()
            assert task_manager is not None
            assert task_manager.max_concurrent_tasks == 3
            assert task_manager.running_tasks == 0
    
    def test_create_task(self, app):
        """Test creating a task"""
        with app.app_context():
            task_manager = TaskManager()
            
            def dummy_task():
                return "completed"
            
            task_id = task_manager.create_task("Test Task", dummy_task)
            
            assert task_id is not None
            assert task_id in task_manager.tasks
            
            task = task_manager.get_task(task_id)
            assert task.name == "Test Task"
            assert task.status == TaskStatus.PENDING
    
    def test_start_task_success(self, app):
        """Test successfully starting a task"""
        with app.app_context():
            task_manager = TaskManager()
            
            def dummy_task():
                time.sleep(0.1)  # Small delay
                return "completed"
            
            task_id = task_manager.create_task("Test Task", dummy_task)
            success = task_manager.start_task(task_id)
            
            assert success == True
            
            task = task_manager.get_task(task_id)
            assert task.status == TaskStatus.RUNNING
            
            # Wait for completion
            time.sleep(0.2)
            
            # Task should be completed
            assert task.status == TaskStatus.COMPLETED
            assert task.result == "completed"
    
    def test_start_task_with_progress(self, app):
        """Test starting a task with progress callback"""
        with app.app_context():
            task_manager = TaskManager()
            
            def dummy_task_with_progress(progress_callback=None):
                if progress_callback:
                    progress_callback(50, "Halfway done")
                time.sleep(0.1)
                if progress_callback:
                    progress_callback(100, "Completed")
                return "completed"
            
            task_id = task_manager.create_task("Test Task with Progress", dummy_task_with_progress)
            task_manager.start_task(task_id)
            
            # Wait for completion
            time.sleep(0.2)
            
            task = task_manager.get_task(task_id)
            assert task.status == TaskStatus.COMPLETED
            assert task.progress == 100
            assert task.current_step == "Completed"
    
    def test_start_task_failure(self, app):
        """Test task failure handling"""
        with app.app_context():
            task_manager = TaskManager()
            
            def failing_task():
                raise Exception("Task failed")
            
            task_id = task_manager.create_task("Failing Task", failing_task)
            task_manager.start_task(task_id)
            
            # Wait for completion
            time.sleep(0.2)
            
            task = task_manager.get_task(task_id)
            assert task.status == TaskStatus.FAILED
            assert "Task failed" in task.error
    
    def test_cancel_task(self, app):
        """Test cancelling a pending task"""
        with app.app_context():
            task_manager = TaskManager()
            
            def dummy_task():
                return "completed"
            
            task_id = task_manager.create_task("Test Task", dummy_task)
            
            # Cancel before starting
            success = task_manager.cancel_task(task_id)
            assert success == True
            
            task = task_manager.get_task(task_id)
            assert task.status == TaskStatus.CANCELLED
    
    def test_get_task_stats(self, app):
        """Test getting task statistics"""
        with app.app_context():
            task_manager = TaskManager()
            
            # Create some tasks
            task_manager.create_task("Task 1", lambda: None)
            task_manager.create_task("Task 2", lambda: None)
            
            stats = task_manager.get_stats()
            
            assert stats['total_tasks'] == 2
            assert stats['running_tasks'] == 0
            assert stats['status_counts']['pending'] == 2
    
    def test_cleanup_old_tasks(self, app):
        """Test cleaning up old tasks"""
        with app.app_context():
            task_manager = TaskManager()
            
            def dummy_task():
                return "completed"
            
            # Create and complete a task
            task_id = task_manager.create_task("Old Task", dummy_task)
            task_manager.start_task(task_id)
            
            # Wait for completion
            time.sleep(0.1)
            
            # Should have 1 task
            assert len(task_manager.tasks) == 1
            
            # Cleanup with very short age (0 hours)
            cleaned = task_manager.cleanup_old_tasks(max_age_hours=0)
            
            # Task should be cleaned up
            assert cleaned == 1
            assert len(task_manager.tasks) == 0


class TestBulkOperations:
    """Test bulk operations functionality"""
    
    def test_bulk_service_creation(self, app):
        """Test creating bulk operations service"""
        with app.app_context():
            bulk_service = BulkOperationsService()
            assert bulk_service is not None
            assert bulk_service.task_manager is not None
    
    @patch('app.services.bulk_operations.ProcessingJob')
    def test_bulk_apply_artwork_selection_explicit(self, mock_processing_job, app, sample_files_with_artwork):
        """Test bulk artwork selection with explicit artwork IDs"""
        with app.app_context():
            bulk_service = BulkOperationsService()
            
            # Get first file and its first artwork option
            from app.models.file_queue import get_queue
            queue = get_queue()
            file_obj = queue.get_file(sample_files_with_artwork[0])
            artwork_id = file_obj.artwork_options[0]['id']
            
            selections = [
                {'file_id': sample_files_with_artwork[0], 'artwork_id': artwork_id}
            ]
            
            result = bulk_service.bulk_apply_artwork_selection(selections)
            
            assert result['total_selections'] == 1
            assert result['successful'] == 1
            assert result['results'][0]['success'] == True
    
    def test_bulk_apply_artwork_selection_strategy(self, app, sample_files_with_artwork):
        """Test bulk artwork selection with strategy"""
        with app.app_context():
            bulk_service = BulkOperationsService()
            
            selections = [
                {'file_id': sample_files_with_artwork[0], 'strategy': 'prefer_embedded'},
                {'file_id': sample_files_with_artwork[1], 'strategy': 'prefer_musicbrainz'}
            ]
            
            result = bulk_service.bulk_apply_artwork_selection(selections)
            
            assert result['total_selections'] == 2
            assert result['successful'] == 2
            
            # Check that strategies were applied
            from app.models.file_queue import get_queue
            queue = get_queue()
            
            file1 = queue.get_file(sample_files_with_artwork[0])
            file2 = queue.get_file(sample_files_with_artwork[1])
            
            # File 1 should have embedded artwork selected
            assert file1.selected_artwork['source'] == 'embedded'
            
            # File 2 should have musicbrainz artwork selected
            assert file2.selected_artwork['source'] == 'musicbrainz'
    
    def test_bulk_selection_strategies(self, app, sample_files_with_artwork):
        """Test different selection strategies"""
        with app.app_context():
            bulk_service = BulkOperationsService()
            
            from app.models.file_queue import get_queue
            queue = get_queue()
            file_obj = queue.get_file(sample_files_with_artwork[0])
            
            # Test each strategy
            strategies = ['prefer_embedded', 'prefer_musicbrainz', 'highest_resolution', 'smallest_file']
            
            for strategy in strategies:
                selected_id = bulk_service._apply_selection_strategy(file_obj, strategy)
                assert selected_id is not None
                assert any(art['id'] == selected_id for art in file_obj.artwork_options)


class TestTaskEndpoints:
    """Test task management API endpoints"""
    
    def test_get_all_tasks_empty(self, client):
        """Test getting all tasks when none exist"""
        response = client.get('/api/tasks')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'tasks' in data
        assert 'total' in data
        assert data['total'] == 0
    
    def test_get_task_stats(self, client):
        """Test getting task statistics"""
        response = client.get('/api/tasks/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_tasks' in data
        assert 'running_tasks' in data
        assert 'status_counts' in data
    
    def test_get_nonexistent_task(self, client):
        """Test getting a non-existent task"""
        response = client.get('/api/tasks/nonexistent-id')
        assert response.status_code == 404
        
        data = response.get_json()
        assert 'Task not found' in data['error']
    
    def test_cleanup_tasks(self, client):
        """Test task cleanup endpoint"""
        response = client.post('/api/tasks/cleanup', json={'max_age_hours': 1})
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'cleaned_count' in data


class TestBulkEndpoints:
    """Test bulk operations API endpoints"""
    
    def test_get_artwork_strategies(self, client):
        """Test getting available artwork strategies"""
        response = client.get('/api/bulk/strategies')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'strategies' in data
        assert len(data['strategies']) > 0
        
        # Check that each strategy has required fields
        for strategy in data['strategies']:
            assert 'id' in strategy
            assert 'name' in strategy
            assert 'description' in strategy
    
    def test_bulk_artwork_select_no_data(self, client):
        """Test bulk artwork selection with no data"""
        response = client.post('/api/bulk/artwork-select', json={})
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'No selections provided' in data['error']
    
    def test_bulk_process_no_data(self, client):
        """Test bulk processing with no data"""
        response = client.post('/api/bulk/process', json={})
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'No file IDs provided' in data['error']
    
    def test_bulk_output_no_data(self, client):
        """Test bulk output with no data"""
        response = client.post('/api/bulk/output', json={})
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'No file IDs provided' in data['error']
    
    def test_get_bulk_stats(self, client):
        """Test getting bulk operation statistics"""
        response = client.get('/api/bulk/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_files' in data
        assert 'files_with_artwork' in data
        assert 'files_with_selection' in data
        assert 'artwork_sources' in data
        assert 'task_stats' in data


if __name__ == '__main__':
    pytest.main([__file__])
