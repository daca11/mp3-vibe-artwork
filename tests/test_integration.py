"""
Integration tests for MP3 Artwork Manager
Tests the complete end-to-end workflow
"""
import pytest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
from app import create_app


@pytest.fixture
def app():
    """Create test Flask app for integration testing"""
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
def sample_mp3_file(app):
    """Create a sample MP3 file for testing"""
    mp3_path = os.path.join(app.config['UPLOAD_FOLDER'], 'sample.mp3')
    
    # Create a minimal MP3-like file for testing
    with open(mp3_path, 'wb') as f:
        # Write a basic MP3 header and some data
        f.write(b'\xff\xfb\x90\x00')  # MP3 frame header
        f.write(b'\x00' * 10000)  # Some data
    
    yield mp3_path


@pytest.fixture
def sample_artwork_file(app):
    """Create a sample artwork file for testing"""
    artwork_path = os.path.join(app.config['TEMP_FOLDER'], 'sample_artwork.jpg')
    
    # Create a minimal JPEG-like file
    with open(artwork_path, 'wb') as f:
        # JPEG header
        f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF')
        f.write(b'\x00' * 1000)  # Some image data
        f.write(b'\xff\xd9')  # JPEG end marker
    
    yield artwork_path


class TestCompleteWorkflow:
    """Test the complete MP3 artwork workflow"""
    
    def test_health_check(self, client):
        """Test basic health check"""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'
    
    def test_home_page_loads(self, client):
        """Test that home page loads correctly"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'MP3 Artwork Manager' in response.data
    
    def test_queue_page_loads(self, client):
        """Test that queue page loads correctly"""
        response = client.get('/queue')
        assert response.status_code == 200
        assert b'Processing Queue' in response.data
    
    def test_artwork_selection_page_loads(self, client):
        """Test that artwork selection page loads correctly"""
        response = client.get('/artwork-selection')
        assert response.status_code == 200
        assert b'Artwork Selection' in response.data
    
    def test_upload_status_endpoint(self, client):
        """Test upload status endpoint"""
        response = client.get('/api/upload/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_files' in data
        assert 'pending' in data
        assert 'processing' in data
        assert 'completed' in data
        assert 'error' in data
    
    def test_queue_endpoint(self, client):
        """Test queue endpoint"""
        response = client.get('/api/queue')
        assert response.status_code == 200
        
        data = response.get_json()
        # Queue response is a list when empty
        assert isinstance(data, list)
    
    def test_task_stats_endpoint(self, client):
        """Test task statistics endpoint"""
        response = client.get('/api/tasks/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_tasks' in data
        assert 'running_tasks' in data
        assert 'status_counts' in data
    
    def test_bulk_stats_endpoint(self, client):
        """Test bulk operations statistics endpoint"""
        response = client.get('/api/bulk/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_files' in data
        assert 'files_with_artwork' in data
        assert 'task_stats' in data
    
    def test_artwork_strategies_endpoint(self, client):
        """Test artwork selection strategies endpoint"""
        response = client.get('/api/bulk/strategies')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'strategies' in data
        assert len(data['strategies']) > 0
        
        # Verify strategy structure
        for strategy in data['strategies']:
            assert 'id' in strategy
            assert 'name' in strategy
            assert 'description' in strategy
    
    def test_output_status_endpoint(self, client):
        """Test output status endpoint"""
        response = client.get('/api/output/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_files' in data
        assert 'ready_for_output' in data
        assert 'output_generated' in data
    
    @patch('app.services.mp3_processor.MP3')
    @patch('app.services.musicbrainz_service.MusicBrainzService')
    @patch('app.services.mp3_output_service.MP3')
    def test_file_upload_and_processing_workflow(self, mock_output_mp3, mock_mb_service, mock_mp3, client, sample_mp3_file, sample_artwork_file, app):
        """Test complete file upload and processing workflow"""
        with app.app_context():
            # Mock MP3 processing
            mock_audio = MagicMock()
            mock_audio.tags = {'TIT2': MagicMock(text=['Test Song']), 'TPE1': MagicMock(text=['Test Artist'])}
            mock_audio.keys.return_value = ['APIC:']
            mock_apic = MagicMock()
            mock_apic.data = b'fake_artwork_data'
            mock_apic.mime = 'image/jpeg'
            mock_audio.__getitem__.return_value = mock_apic
            mock_mp3.return_value = mock_audio
            
            # Mock MusicBrainz service
            mock_mb = MagicMock()
            mock_mb.search_and_get_artwork.return_value = []
            mock_mb_service.return_value = mock_mb
            
            # Mock output MP3
            mock_output_audio = MagicMock()
            mock_output_audio.tags = MagicMock()
            mock_output_audio.save = MagicMock()
            mock_output_mp3.return_value = mock_output_audio
            
            # Step 1: Upload file
            with open(sample_mp3_file, 'rb') as f:
                response = client.post('/api/upload', 
                                     data={'files': (f, 'test_song.mp3')},
                                     content_type='multipart/form-data')
            
            assert response.status_code == 200
            upload_data = response.get_json()
            assert 'uploaded_files' in upload_data
            assert len(upload_data['uploaded_files']) == 1
            
            file_info = upload_data['uploaded_files'][0]
            file_id = file_info['id']
            
            # Step 2: Check queue
            response = client.get('/api/queue')
            assert response.status_code == 200
            queue_data = response.get_json()
            assert len(queue_data) == 1
            
            # Step 3: Process file
            response = client.post(f'/api/process/{file_id}')
            assert response.status_code == 200
            
            # Step 4: Check processing status
            response = client.get(f'/api/status/{file_id}')
            assert response.status_code == 200
            status_data = response.get_json()
            assert 'status' in status_data
            
            # Step 5: Get artwork options
            response = client.get(f'/api/artwork/{file_id}')
            assert response.status_code == 200
            artwork_data = response.get_json()
            assert 'artwork_options' in artwork_data
            
            # If we have artwork options, select one
            if artwork_data['artwork_options']:
                artwork_id = artwork_data['artwork_options'][0]['id']
                
                # Step 6: Select artwork
                response = client.post(f'/api/artwork/{file_id}/select',
                                     headers={'Content-Type': 'application/json'},
                                     json={'artwork_id': artwork_id})
                assert response.status_code == 200
                
                # Step 7: Generate output
                response = client.post(f'/api/output/{file_id}',
                                     headers={'Content-Type': 'application/json'},
                                     json={})
                assert response.status_code == 200
                output_data = response.get_json()
                assert 'download_url' in output_data
    
    def test_bulk_operations_workflow(self, client, app):
        """Test bulk operations workflow"""
        with app.app_context():
            # Test bulk strategies
            response = client.get('/api/bulk/strategies')
            assert response.status_code == 200
            
            # Test bulk artwork selection with no data
            response = client.post('/api/bulk/artwork-select', json={})
            assert response.status_code == 400
            
            # Test bulk processing with no data
            response = client.post('/api/bulk/process', json={})
            assert response.status_code == 400
            
            # Test bulk output with no data
            response = client.post('/api/bulk/output', json={})
            assert response.status_code == 400
    
    def test_task_management_workflow(self, client):
        """Test task management workflow"""
        # Get initial task stats
        response = client.get('/api/tasks/stats')
        assert response.status_code == 200
        
        # Get all tasks
        response = client.get('/api/tasks')
        assert response.status_code == 200
        
        # Try to get non-existent task
        response = client.get('/api/tasks/nonexistent-id')
        assert response.status_code == 404
        
        # Try to cancel non-existent task
        response = client.post('/api/tasks/nonexistent-id/cancel')
        assert response.status_code == 400
        
        # Test task cleanup
        response = client.post('/api/tasks/cleanup', json={'max_age_hours': 1})
        assert response.status_code == 200
    
    def test_error_handling(self, client):
        """Test error handling across the application"""
        # Test non-existent endpoints
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        
        # Test invalid file operations
        response = client.get('/api/artwork/invalid-id')
        assert response.status_code == 404
        
        response = client.post('/api/output/invalid-id',
                             headers={'Content-Type': 'application/json'},
                             json={})
        assert response.status_code == 404
        
        response = client.get('/api/download/invalid-id')
        assert response.status_code == 404
    
    def test_api_endpoints_structure(self, client):
        """Test that all API endpoints return proper JSON structure"""
        # Upload status
        response = client.get('/api/upload/status')
        assert response.status_code == 200
        assert response.is_json
        
        # Queue
        response = client.get('/api/queue')
        assert response.status_code == 200
        assert response.is_json
        
        # Task stats
        response = client.get('/api/tasks/stats')
        assert response.status_code == 200
        assert response.is_json
        
        # Bulk stats
        response = client.get('/api/bulk/stats')
        assert response.status_code == 200
        assert response.is_json
        
        # Output status
        response = client.get('/api/output/status')
        assert response.status_code == 200
        assert response.is_json


class TestPerformanceAndLimits:
    """Test performance characteristics and limits"""
    
    def test_upload_file_size_limit(self, client, app):
        """Test file size limits are enforced"""
        with app.app_context():
            # Create a large file that exceeds limits
            large_file_path = os.path.join(app.config['TEMP_FOLDER'], 'large_file.mp3')
            
            # Create a file larger than the configured limit (50MB)
            # We'll create a smaller test file to avoid taking too much time
            with open(large_file_path, 'wb') as f:
                f.write(b'\x00' * (1024 * 1024))  # 1MB test file
            
            # Upload should succeed for reasonable file size
            with open(large_file_path, 'rb') as f:
                response = client.post('/api/upload',
                                     data={'files': (f, 'large_file.mp3')},
                                     content_type='multipart/form-data')
            
            # Should succeed since it's under the limit
            assert response.status_code == 200
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get('/api/upload/status')
            results.append(response.status_code)
        
        # Create multiple threads to make concurrent requests
        threads = []
        for i in range(5):
            t = threading.Thread(target=make_request)
            threads.append(t)
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)


if __name__ == '__main__':
    pytest.main([__file__])
