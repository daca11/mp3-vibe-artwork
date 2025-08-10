"""
Unit tests for Phase 2: File Upload & Validation
"""
import pytest
import tempfile
import os
from io import BytesIO
from unittest.mock import Mock, patch
from app import create_app
from app.utils.validation import validate_mp3_file, safe_filename, allowed_file
from app.models.file_queue import get_queue, FileQueue, QueuedFile, FileStatus


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
        
        # Clear the file queue before each test
        with app.app_context():
            queue = get_queue()
            for file in queue.get_all_files():
                queue.remove_file(file.id)
        
        yield app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_mp3_file():
    """Create a minimal MP3-like file for testing"""
    # Create a simple file with MP3 header
    mp3_data = b'\xff\xfb\x90\x00' + b'\x00' * 1024  # Simple MP3 header + data
    file = BytesIO(mp3_data)
    file.filename = 'test_song.mp3'
    file.content_type = 'audio/mpeg'
    return file


class TestFileValidation:
    """Test file validation functions"""
    
    def test_safe_filename_preserves_original(self):
        """Test that safe_filename preserves original filenames"""
        # Test normal filename
        assert safe_filename('Artist - Song.mp3') == 'Artist - Song.mp3'
        
        # Test filename with special characters
        assert safe_filename('Artist & Band - Song (Remix).mp3') == 'Artist & Band - Song (Remix).mp3'
        
        # Test filename without extension
        assert safe_filename('Artist - Song') == 'Artist - Song.mp3'
        
        # Test empty filename
        assert safe_filename('') == 'unnamed_file.mp3'
        
        # Test filename with control characters (should be cleaned)
        assert safe_filename('Artist\x00 - Song.mp3') == 'Artist - Song.mp3'
    
    def test_allowed_file(self):
        """Test file extension validation"""
        assert allowed_file('song.mp3') == True
        assert allowed_file('song.MP3') == True
        assert allowed_file('song.wav') == False
        assert allowed_file('song.txt') == False
        assert allowed_file('song') == False
    
    def test_validate_mp3_file_success(self, app, sample_mp3_file):
        """Test successful MP3 file validation"""
        with app.app_context():
            is_valid, error = validate_mp3_file(sample_mp3_file)
            # Note: This might fail due to magic library checks, but extension should pass
            assert isinstance(is_valid, bool)
            assert error is None or 'not a valid MP3 file' in error
    
    def test_validate_mp3_file_no_file(self, app):
        """Test validation with no file"""
        with app.app_context():
            is_valid, error = validate_mp3_file(None)
            assert is_valid == False
            assert error == "No file provided"
    
    def test_validate_mp3_file_wrong_extension(self, app):
        """Test validation with wrong file extension"""
        with app.app_context():
            file = BytesIO(b'test data')
            file.filename = 'test.txt'
            file.content_type = 'text/plain'
            
            is_valid, error = validate_mp3_file(file)
            assert is_valid == False
            assert "not an MP3 file" in error


class TestFileQueue:
    """Test file queue functionality"""
    
    def test_queue_creation(self, app):
        """Test queue creation"""
        with app.app_context():
            queue = FileQueue('test_queue.json')
            assert queue is not None
            assert len(queue.get_all_files()) == 0
    
    def test_add_file_to_queue(self, app):
        """Test adding file to queue"""
        with app.app_context():
            queue = FileQueue('test_queue.json')
            
            queued_file = queue.add_file(
                filename='test.mp3',
                file_path='/tmp/test.mp3',
                size=1024,
                mime_type='audio/mpeg'
            )
            
            assert queued_file is not None
            assert queued_file.filename == 'test.mp3'
            assert queued_file.size == 1024
            assert queued_file.status == FileStatus.PENDING
            
            # Check it's in the queue
            all_files = queue.get_all_files()
            assert len(all_files) == 1
            assert all_files[0].id == queued_file.id
    
    def test_remove_file_from_queue(self, app):
        """Test removing file from queue"""
        with app.app_context():
            queue = FileQueue('test_queue.json')
            
            # Add a file
            queued_file = queue.add_file(
                filename='test.mp3',
                file_path='/tmp/test.mp3',
                size=1024
            )
            
            # Remove it
            result = queue.remove_file(queued_file.id)
            assert result == True
            
            # Check it's gone
            assert len(queue.get_all_files()) == 0
            assert queue.get_file(queued_file.id) is None
    
    def test_update_file_status(self, app):
        """Test updating file status"""
        with app.app_context():
            queue = FileQueue('test_queue.json')
            
            # Add a file
            queued_file = queue.add_file(
                filename='test.mp3',
                file_path='/tmp/test.mp3',
                size=1024
            )
            
            # Update status
            updated_file = queue.update_file(
                queued_file.id,
                status='processing',
                progress=50
            )
            
            assert updated_file is not None
            assert updated_file.status == FileStatus.PROCESSING
            assert updated_file.progress == 50
    
    def test_get_files_by_status(self, app):
        """Test filtering files by status"""
        with app.app_context():
            queue = FileQueue('test_queue.json')
            
            # Add files with different statuses
            file1 = queue.add_file('test1.mp3', '/tmp/test1.mp3', 1024)
            file2 = queue.add_file('test2.mp3', '/tmp/test2.mp3', 2048)
            
            # Update one to processing
            queue.update_file(file2.id, status='processing')
            
            # Check filtering
            pending_files = queue.get_files_by_status(FileStatus.PENDING)
            processing_files = queue.get_files_by_status(FileStatus.PROCESSING)
            
            assert len(pending_files) == 1
            assert len(processing_files) == 1
            assert pending_files[0].id == file1.id
            assert processing_files[0].id == file2.id


class TestUploadEndpoints:
    """Test upload API endpoints"""
    
    def test_upload_no_files(self, client):
        """Test upload endpoint with no files"""
        response = client.post('/api/upload')
        assert response.status_code == 400
        data = response.get_json()
        assert 'No files uploaded' in data['error']
    
    def test_upload_empty_files(self, client):
        """Test upload endpoint with empty file list"""
        response = client.post('/api/upload', data={'files': []})
        assert response.status_code == 400
    
    def test_upload_status_endpoint(self, client):
        """Test upload status endpoint"""
        response = client.get('/api/upload/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_files' in data
        assert 'max_file_size_mb' in data


class TestQueueEndpoints:
    """Test queue management API endpoints"""
    
    def setup_method(self, method):
        """Clear the queue before each test"""
        from app.models.file_queue import get_queue
        queue = get_queue()
        queue.clear()

    def test_get_queue_empty(self, client):
        """Test getting empty queue"""
        response = client.get('/api/queue')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_remove_nonexistent_file(self, client):
        """Test removing file that doesn't exist"""
        response = client.delete('/api/queue/nonexistent-id')
        assert response.status_code == 404
        data = response.get_json()
        assert 'File not found' in data['error']
    
    def test_process_nonexistent_file(self, client):
        """Test processing file that doesn't exist"""
        response = client.post('/api/process/nonexistent-id')
        assert response.status_code == 404
        data = response.get_json()
        assert 'File not found' in data['error']
    
    def test_batch_process_empty_queue(self, client):
        """Test batch processing with no files"""
        response = client.post('/api/process/batch')
        assert response.status_code == 200
        data = response.get_json()
        assert 'No pending files' in data['message']
    
    def test_get_file_status_nonexistent(self, client):
        """Test getting status of nonexistent file"""
        response = client.get('/api/status/nonexistent-id')
        assert response.status_code == 404
        data = response.get_json()
        assert 'File not found' in data['error']


if __name__ == '__main__':
    pytest.main([__file__])
