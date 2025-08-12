"""
Unit tests for Phase 7: File Processing & Output
"""
import pytest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
from app import create_app
from app.services.mp3_output_service import MP3OutputService, MP3OutputError


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
def mock_mp3_file(app):
    """Create a mock MP3 file for testing"""
    with app.app_context():
        mp3_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test.mp3')
        
        # Create a minimal MP3-like file
        with open(mp3_path, 'wb') as f:
            # Write minimal MP3 header
            f.write(b'\xff\xfb\x90\x00')  # Basic MP3 frame header
            f.write(b'\x00' * 1000)  # Padding
        
        yield mp3_path


@pytest.fixture
def mock_artwork_file(app):
    """Create a mock artwork file for testing"""
    with app.app_context():
        artwork_path = os.path.join(app.config['TEMP_FOLDER'], 'test_artwork.jpg')
        
        # Create a minimal JPEG-like file
        with open(artwork_path, 'wb') as f:
            # JPEG header
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF')
            f.write(b'\x00' * 100)  # Minimal JPEG data
            f.write(b'\xff\xd9')  # JPEG end marker
        
        yield artwork_path


@pytest.fixture
def sample_file_with_selection(app, mock_mp3_file, mock_artwork_file):
    """Create a sample file with selected artwork"""
    with app.app_context():
        from app.models.file_queue import get_queue
        queue = get_queue()
        
        # Create a test file
        queued_file = queue.add_file(
            filename='test_song.mp3',
            file_path=mock_mp3_file,
            size=1024000,
            mime_type='audio/mpeg'
        )
        
        # Add and select artwork
        queued_file.add_artwork_option(
            source='embedded',
            image_path=mock_artwork_file,
            dimensions={'width': 600, 'height': 600},
            file_size=150000,
            metadata={'format': 'JPEG', 'description': 'Front cover'}
        )
        
        # Select the artwork
        artwork_id = queued_file.artwork_options[0]['id']
        queued_file.select_artwork(artwork_id)
        
        queue._save_queue()
        
        yield queued_file.id
        
        # Cleanup
        queue.remove_file(queued_file.id)


class TestMP3OutputService:
    """Test MP3 output service functionality"""
    
    def test_service_creation(self, app):
        """Test creating MP3 output service"""
        with app.app_context():
            service = MP3OutputService()
            assert service is not None
    
    @patch('app.services.mp3_output_service.MP3')
    @patch('shutil.copy2')
    def test_embed_artwork_success(self, mock_copy, mock_mp3, app, mock_mp3_file, mock_artwork_file):
        """Test successful artwork embedding"""
        with app.app_context():
            # Mock MP3 file
            mock_audio = MagicMock()
            mock_audio.tags = MagicMock()
            mock_audio.keys.return_value = []
            mock_audio.add_tags = MagicMock()
            mock_audio.save = MagicMock()
            mock_mp3.return_value = mock_audio
            
            service = MP3OutputService()
            
            result = service.embed_artwork(
                mp3_file_path=mock_mp3_file,
                artwork_path=mock_artwork_file
            )
            
            assert result['success'] == True
            assert 'output_path' in result
            assert 'artwork_embedded' in result
            assert result['artwork_embedded'] == True
    
    def test_embed_artwork_missing_mp3(self, app, mock_artwork_file):
        """Test embedding with missing MP3 file"""
        with app.app_context():
            service = MP3OutputService()
            
            with pytest.raises(MP3OutputError):
                service.embed_artwork(
                    mp3_file_path='/nonexistent/file.mp3',
                    artwork_path=mock_artwork_file
                )
    
    def test_embed_artwork_missing_artwork(self, app, mock_mp3_file):
        """Test embedding with missing artwork file"""
        with app.app_context():
            service = MP3OutputService()
            
            with pytest.raises(MP3OutputError):
                service.embed_artwork(
                    mp3_file_path=mock_mp3_file,
                    artwork_path='/nonexistent/artwork.jpg'
                )
    
    @patch('app.services.mp3_output_service.MP3')
    def test_validate_output_file_success(self, mock_mp3, app):
        """Test successful output file validation"""
        with app.app_context():
            # Mock valid MP3 file
            mock_audio = MagicMock()
            mock_audio.info = MagicMock()
            mock_audio.info.length = 180.0
            mock_audio.info.bitrate = 320
            mock_audio.info.sample_rate = 44100
            mock_audio.keys.return_value = ['APIC:']
            
            mock_apic = MagicMock()
            mock_apic.mime = 'image/jpeg'
            mock_apic.type = 3
            mock_apic.desc = 'Front Cover'
            mock_apic.data = b'fake_image_data'
            mock_audio.__getitem__.return_value = mock_apic
            
            mock_mp3.return_value = mock_audio
            
            # Create a test file
            test_file = os.path.join(app.config['OUTPUT_FOLDER'], 'test.mp3')
            with open(test_file, 'wb') as f:
                f.write(b'fake mp3 data')
            
            service = MP3OutputService()
            result = service.validate_output_file(test_file)
            
            assert result['valid'] == True
            assert result['has_artwork'] == True
            assert 'artwork_info' in result
    
    def test_validate_output_file_missing(self, app):
        """Test validation of missing file"""
        with app.app_context():
            service = MP3OutputService()
            result = service.validate_output_file('/nonexistent/file.mp3')
            
            assert result['valid'] == False
            assert 'File not found' in result['error']
    
    def test_cleanup_temp_files(self, app):
        """Test cleanup of temporary files"""
        with app.app_context():
            service = MP3OutputService()
            
            # Create some temporary files
            temp_files = []
            for i in range(3):
                temp_path = os.path.join(app.config['TEMP_FOLDER'], f'temp_{i}.tmp')
                with open(temp_path, 'w') as f:
                    f.write('temporary data')
                temp_files.append(temp_path)
            
            # Cleanup
            cleaned = service.cleanup_temp_files(temp_files)
            
            assert cleaned == 3
            for temp_path in temp_files:
                assert not os.path.exists(temp_path)


class TestOutputEndpoints:
    """Test output API endpoints"""
    
    def test_generate_output_nonexistent_file(self, client):
        """Test generating output for non-existent file"""
        response = client.post('/api/output/nonexistent-id', 
                             headers={'Content-Type': 'application/json'},
                             json={})
        assert response.status_code == 404
        data = response.get_json()
        assert 'File not found' in data['error']
    
    def test_generate_output_no_selection(self, client, app):
        """Test generating output when no artwork is selected"""
        with app.app_context():
            from app.models.file_queue import get_queue
            queue = get_queue()
            
            # Create a file without selected artwork
            queued_file = queue.add_file(
                filename='test_no_selection.mp3',
                file_path='/tmp/test.mp3',
                size=1024000,
                mime_type='audio/mpeg'
            )
            
            response = client.post(f'/api/output/{queued_file.id}',
                                 headers={'Content-Type': 'application/json'},
                                 json={})
            assert response.status_code == 400
            data = response.get_json()
            assert 'No artwork selected' in data['error']
            
            # Cleanup
            queue.remove_file(queued_file.id)
    
    def test_output_status(self, client):
        """Test getting output status"""
        response = client.get('/api/output/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_files' in data
        assert 'ready_for_output' in data
        assert 'output_generated' in data
        assert 'pending_selection' in data
        assert 'no_artwork' in data
    
    def test_validate_output_nonexistent_file(self, client):
        """Test validating output for non-existent file"""
        response = client.get('/api/validate/nonexistent-id')
        assert response.status_code == 404
    
    def test_download_nonexistent_file(self, client):
        """Test downloading non-existent file"""
        response = client.get('/api/download/nonexistent-id')
        assert response.status_code == 404
    
    def test_download_archive_nonexistent(self, client):
        """Test downloading non-existent archive"""
        response = client.get('/api/download/archive/nonexistent.zip')
        assert response.status_code == 404
    
    def test_download_archive_invalid_extension(self, client):
        """Test downloading archive with invalid extension"""
        response = client.get('/api/download/archive/test.txt')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid archive file' in data['error']
    
    def test_batch_output_no_files(self, client):
        """Test batch output with no file IDs"""
        response = client.post('/api/output/batch', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'No file IDs provided' in data['error']
    
    def test_batch_output_nonexistent_files(self, client):
        """Test batch output with non-existent files"""
        response = client.post('/api/output/batch', json={
            'file_ids': ['nonexistent-1', 'nonexistent-2']
        })
        assert response.status_code == 404
    
    def test_cleanup_no_data(self, client):
        """Test cleanup with no data"""
        response = client.post('/api/output/cleanup', json={})
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'files_cleaned' in data


class TestOutputIntegration:
    """Test integrated output functionality"""
    
    @patch('app.services.mp3_output_service.MP3OutputService.embed_artwork')
    def test_generate_output_integration(self, mock_embed, client, sample_file_with_selection, app):
        """Test integrated output generation"""
        with app.app_context():
            # Mock successful embedding
            mock_embed.return_value = {
                'success': True,
                'output_path': '/tmp/output.mp3',
                'original_size': 1000000,
                'output_size': 1150000,
                'artwork_size': 150000,
                'size_increase': 150000,
                'mime_type': 'image/jpeg',
                'artwork_embedded': True
            }
            
            response = client.post(f'/api/output/{sample_file_with_selection}',
                                 headers={'Content-Type': 'application/json'},
                                 json={})
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'output_filename' in data
            assert 'download_url' in data
            assert data['artwork_embedded'] == True
    
    @patch('app.services.mp3_output_service.MP3OutputService.process_file_with_selection')
    def test_batch_output_integration(self, mock_process, client, sample_file_with_selection, app):
        """Test integrated batch output generation"""
        with app.app_context():
            # Mock successful processing
            mock_process.return_value = {
                'success': True,
                'output_path': '/tmp/output.mp3',
                'output_filename': 'test.mp3',
                'original_size': 1000000,
                'output_size': 1150000,
                'artwork_embedded': True
            }
            
            response = client.post('/api/output/batch', json={
                'file_ids': [sample_file_with_selection],
                'create_zip': False
            })
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['successful'] == 1
            assert data['failed'] == 0
            assert len(data['results']) == 1


if __name__ == '__main__':
    pytest.main([__file__])
