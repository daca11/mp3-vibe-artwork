"""
Unit tests for Phase 3: MP3 Processing & Metadata
"""
import pytest
import tempfile
import os
from io import BytesIO
from unittest.mock import Mock, patch
from app import create_app
from app.services.mp3_processor import MP3Processor, MP3ProcessingError
from app.models.processing_job import ProcessingJob, ProcessingStep
from app.models.file_queue import FileQueue, QueuedFile


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
def sample_mp3_path(app):
    """Create a sample MP3 file for testing"""
    # Create a minimal MP3-like file
    mp3_data = b'\xff\xfb\x90\x00' + b'\x00' * 2048  # Simple MP3 header + data
    
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, 
        suffix='.mp3',
        dir=app.config['UPLOAD_FOLDER']
    )
    temp_file.write(mp3_data)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


class TestMP3Processor:
    """Test MP3 processor service"""
    
    def test_processor_creation(self, app):
        """Test creating MP3 processor"""
        with app.app_context():
            processor = MP3Processor()
            assert processor is not None
            assert processor.supported_image_formats == ['JPEG', 'PNG']
    
    def test_parse_filename_metadata(self, app):
        """Test filename parsing for metadata"""
        with app.app_context():
            processor = MP3Processor()
            
            # Test standard format
            result = processor.parse_filename_metadata('Artist - Song Title.mp3')
            assert result['artist'] == 'Artist'
            assert result['title'] == 'Song Title'
            
            # Test with special characters
            result = processor.parse_filename_metadata('The Beatles - Hey Jude.mp3')
            assert result['artist'] == 'The Beatles'
            assert result['title'] == 'Hey Jude'
            
            # Test underscore format
            result = processor.parse_filename_metadata('Artist_-_Song.mp3')
            assert result['artist'] == 'Artist'
            assert result['title'] == 'Song'
            
            # Test no separator
            result = processor.parse_filename_metadata('RandomSong.mp3')
            assert result['artist'] is None
            assert result['title'] == 'RandomSong'
    
    @patch('mutagen.mp3.MP3')
    def test_extract_metadata_success(self, mock_mp3, app):
        """Test successful metadata extraction"""
        with app.app_context():
            # Mock MP3 file with metadata
            mock_file = Mock()
            mock_file.info.length = 180.5
            mock_file.info.bitrate = 320
            mock_file.info.sample_rate = 44100
            mock_file.info.channels = 2
            
            mock_file.tags = {
                'TIT2': Mock(),
                'TPE1': Mock(),
                'TALB': Mock()
            }
            mock_file.tags['TIT2'].__str__ = Mock(return_value='Test Song')
            mock_file.tags['TPE1'].__str__ = Mock(return_value='Test Artist')
            mock_file.tags['TALB'].__str__ = Mock(return_value='Test Album')
            mock_file.tags.version = (2, 4, 0)
            
            mock_mp3.return_value = mock_file
            
            processor = MP3Processor()
            metadata = processor.extract_metadata('/fake/path.mp3')
            
            assert metadata['duration'] == 180.5
            assert metadata['bitrate'] == 320
            assert metadata['title'] == 'Test Song'
            assert metadata['artist'] == 'Test Artist'
            assert metadata['album'] == 'Test Album'
            assert metadata['has_id3'] == True
    
    @patch('mutagen.mp3.MP3')
    def test_extract_metadata_no_tags(self, mock_mp3, app):
        """Test metadata extraction with no ID3 tags"""
        with app.app_context():
            # Mock MP3 file without tags
            mock_file = Mock()
            mock_file.info.length = 120.0
            mock_file.info.bitrate = 128
            mock_file.info.sample_rate = 44100
            mock_file.info.channels = 2
            mock_file.tags = None
            
            mock_mp3.return_value = mock_file
            
            processor = MP3Processor()
            metadata = processor.extract_metadata('/fake/path.mp3')
            
            assert metadata['duration'] == 120.0
            assert metadata['bitrate'] == 128
            assert metadata['title'] is None
            assert metadata['artist'] is None
            assert metadata['has_id3'] == False
    
    @patch('mutagen.mp3.MP3')
    def test_extract_embedded_artwork(self, mock_mp3, app):
        """Test embedded artwork extraction"""
        with app.app_context():
            # Mock MP3 file with artwork
            mock_apic = Mock()
            mock_apic.data = b'\xff\xd8\xff' + b'\x00' * 1000  # JPEG header + data
            mock_apic.mime = 'image/jpeg'
            mock_apic.type = 3  # Cover front
            mock_apic.desc = 'Cover'
            
            mock_file = Mock()
            mock_file.tags.getall.return_value = [mock_apic]
            mock_mp3.return_value = mock_file
            
            # Mock PIL Image
            with patch('PIL.Image.open') as mock_image:
                mock_img = Mock()
                mock_img.size = (500, 500)
                mock_img.format = 'JPEG'
                mock_image.return_value.__enter__.return_value = mock_img
                
                processor = MP3Processor()
                artwork_list = processor.extract_embedded_artwork('/fake/path.mp3')
                
                assert len(artwork_list) == 1
                artwork = artwork_list[0]
                assert artwork['source'] == 'embedded'
                assert artwork['dimensions']['width'] == 500
                assert artwork['dimensions']['height'] == 500
                assert artwork['format'] == 'JPEG'
    
    def test_get_search_terms_with_metadata(self, app):
        """Test getting search terms from ID3 metadata"""
        with app.app_context():
            processor = MP3Processor()
            
            # Mock extract_metadata to return data
            with patch.object(processor, 'extract_metadata') as mock_extract:
                mock_extract.return_value = {
                    'artist': 'Test Artist',
                    'title': 'Test Song',
                    'album': 'Test Album'
                }
                
                search_terms = processor.get_search_terms('/fake/path.mp3', 'Test - Song.mp3')
                
                assert search_terms['artist'] == 'Test Artist'
                assert search_terms['title'] == 'Test Song'
                assert search_terms['album'] == 'Test Album'
                assert search_terms['source'] == 'id3_tags'
    
    def test_get_search_terms_fallback_to_filename(self, app):
        """Test fallback to filename parsing when no ID3 tags"""
        with app.app_context():
            processor = MP3Processor()
            
            # Mock extract_metadata to return no artist/title
            with patch.object(processor, 'extract_metadata') as mock_extract:
                mock_extract.return_value = {
                    'artist': None,
                    'title': None,
                    'album': None
                }
                
                search_terms = processor.get_search_terms('/fake/path.mp3', 'Artist - Song.mp3')
                
                assert search_terms['artist'] == 'Artist'
                assert search_terms['title'] == 'Song'
                assert search_terms['source'] == 'filename_parsing'


class TestProcessingJob:
    """Test processing job functionality"""
    
    def test_job_creation(self):
        """Test creating a processing job"""
        job = ProcessingJob('test-file-id')
        
        assert job.file_id == 'test-file-id'
        assert job.current_step == ProcessingStep.INITIALIZING
        assert job.progress_percent == 0
        assert job.error_message is None
        assert len(job.steps_completed) == 0
    
    def test_update_step(self):
        """Test updating processing step"""
        job = ProcessingJob('test-file-id')
        
        # Test normal step update
        job.update_step(ProcessingStep.EXTRACTING_METADATA)
        assert job.current_step == ProcessingStep.EXTRACTING_METADATA
        assert ProcessingStep.EXTRACTING_METADATA in job.steps_completed
        assert job.progress_percent > 0
        
        # Test completion
        job.update_step(ProcessingStep.COMPLETED)
        assert job.current_step == ProcessingStep.COMPLETED
        assert job.progress_percent == 100
        assert job.completed_at is not None
        
        # Test error
        job = ProcessingJob('test-file-id-2')
        job.update_step(ProcessingStep.FAILED, "Test error")
        assert job.current_step == ProcessingStep.FAILED
        assert job.error_message == "Test error"
        assert job.completed_at is not None
    
    def test_to_dict(self):
        """Test converting job to dictionary"""
        job = ProcessingJob('test-file-id')
        job.update_step(ProcessingStep.EXTRACTING_METADATA)
        
        job_dict = job.to_dict()
        
        assert job_dict['file_id'] == 'test-file-id'
        assert job_dict['current_step'] == 'extracting_metadata'
        assert 'started_at' in job_dict
        assert 'progress_percent' in job_dict


class TestProcessingEndpoints:
    """Test processing API endpoints"""
    
    def test_process_nonexistent_file(self, client):
        """Test processing a file that doesn't exist"""
        response = client.post('/api/process/nonexistent-id')
        assert response.status_code == 404
        data = response.get_json()
        assert 'File not found' in data['error']
    
    def test_process_file_invalid_status(self, client, app):
        """Test processing a file that's not pending"""
        with app.app_context():
            # Add a file to queue with completed status
            from app.models.file_queue import get_queue
            queue = get_queue()
            file_obj = queue.add_file('test.mp3', '/tmp/test.mp3', 1024)
            queue.update_file(file_obj.id, status='completed')
            
            response = client.post(f'/api/process/{file_obj.id}')
            assert response.status_code == 400
            data = response.get_json()
            assert 'not pending' in data['error']


if __name__ == '__main__':
    pytest.main([__file__])
