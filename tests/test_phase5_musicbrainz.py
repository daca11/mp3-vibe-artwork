"""
Unit tests for Phase 5: MusicBrainz Integration
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import requests
from app import create_app
from app.services.musicbrainz_service import MusicBrainzService, MusicBrainzError


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
def mock_musicbrainz_response():
    """Mock MusicBrainz search response"""
    return {
        'release-list': [
            {
                'id': 'test-release-id-1',
                'title': 'Test Album',
                'artist-credit': [
                    {'artist': {'name': 'Test Artist'}}
                ],
                'date': '2023-01-01',
                'country': 'US'
            },
            {
                'id': 'test-release-id-2',
                'title': 'Another Album',
                'artist-credit': [
                    {'artist': {'name': 'Test Artist'}}
                ],
                'date': '2022-12-01',
                'country': 'UK'
            }
        ]
    }


@pytest.fixture
def mock_coverart_response():
    """Mock Cover Art Archive response"""
    return {
        'images': [
            {
                'image': 'https://coverartarchive.org/release/test-release-id-1/123456-front.jpg',
                'thumbnails': {
                    'large': 'https://coverartarchive.org/release/test-release-id-1/123456-500.jpg',
                    '500': 'https://coverartarchive.org/release/test-release-id-1/123456-500.jpg',
                    '250': 'https://coverartarchive.org/release/test-release-id-1/123456-250.jpg'
                },
                'types': ['Front'],
                'approved': True,
                'comment': 'Front cover'
            },
            {
                'image': 'https://coverartarchive.org/release/test-release-id-1/789012-back.jpg',
                'thumbnails': {
                    'large': 'https://coverartarchive.org/release/test-release-id-1/789012-500.jpg'
                },
                'types': ['Back'],
                'approved': True,
                'comment': 'Back cover'
            }
        ]
    }


class TestMusicBrainzService:
    """Test MusicBrainz service functionality"""
    
    def test_service_creation(self, app):
        """Test creating MusicBrainz service"""
        with app.app_context():
            service = MusicBrainzService()
            assert service is not None
            assert service.rate_limit_delay == 1.0
            assert service.timeout == 10
    
    @patch('musicbrainzngs.search_releases')
    def test_search_releases_success(self, mock_search, app, mock_musicbrainz_response):
        """Test successful release search"""
        with app.app_context():
            mock_search.return_value = mock_musicbrainz_response
            
            service = MusicBrainzService()
            service.rate_limit_delay = 0  # Disable rate limiting for tests
            
            releases = service.search_releases('Test Artist', 'Test Song')
            
            assert len(releases) == 2
            assert releases[0]['id'] == 'test-release-id-1'
            assert releases[0]['title'] == 'Test Album'
            assert releases[0]['artist'] == 'Test Artist'
            assert releases[0]['source'] == 'musicbrainz'
    
    @patch('musicbrainzngs.search_releases')
    def test_search_releases_no_results(self, mock_search, app):
        """Test search with no results"""
        with app.app_context():
            mock_search.return_value = {'release-list': []}
            
            service = MusicBrainzService()
            service.rate_limit_delay = 0
            
            releases = service.search_releases('Unknown Artist', 'Unknown Song')
            
            assert len(releases) == 0
    
    @patch('musicbrainzngs.search_releases')
    def test_search_releases_error(self, mock_search, app):
        """Test search with MusicBrainz error"""
        with app.app_context():
            mock_search.side_effect = Exception("MusicBrainz API error")
            
            service = MusicBrainzService()
            service.rate_limit_delay = 0
            
            with pytest.raises(MusicBrainzError):
                service.search_releases('Test Artist', 'Test Song')
    
    def test_parse_release(self, app):
        """Test parsing release data"""
        with app.app_context():
            service = MusicBrainzService()
            
            release_data = {
                'id': 'test-id',
                'title': 'Test Album',
                'artist-credit': [{'artist': {'name': 'Test Artist'}}],
                'date': '2023-01-01',
                'country': 'US'
            }
            
            parsed = service._parse_release(release_data)
            
            assert parsed is not None
            assert parsed['id'] == 'test-id'
            assert parsed['title'] == 'Test Album'
            assert parsed['artist'] == 'Test Artist'
            assert parsed['date'] == '2023-01-01'
            assert parsed['country'] == 'US'
            assert parsed['score'] > 50  # Should have bonus points for having data
    
    @patch('requests.get')
    def test_get_cover_art_success(self, mock_get, app, mock_coverart_response):
        """Test successful cover art retrieval"""
        with app.app_context():
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_coverart_response
            mock_get.return_value = mock_response
            
            service = MusicBrainzService()
            service.rate_limit_delay = 0
            
            artwork = service.get_cover_art('test-release-id-1')
            
            assert len(artwork) == 2
            assert artwork[0]['source'] == 'musicbrainz'
            assert artwork[0]['is_front'] == True
            assert artwork[1]['is_front'] == False
            assert 'image_url' in artwork[0]
    
    @patch('requests.get')
    def test_get_cover_art_not_found(self, mock_get, app):
        """Test cover art retrieval when no artwork exists"""
        with app.app_context():
            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            service = MusicBrainzService()
            service.rate_limit_delay = 0
            
            artwork = service.get_cover_art('nonexistent-release-id')
            
            assert len(artwork) == 0
    
    @patch('requests.get')
    def test_get_cover_art_error(self, mock_get, app):
        """Test cover art retrieval with network error"""
        with app.app_context():
            mock_get.side_effect = requests.RequestException("Network error")
            
            service = MusicBrainzService()
            service.rate_limit_delay = 0
            
            with pytest.raises(MusicBrainzError):
                service.get_cover_art('test-release-id')
    
    def test_parse_cover_art(self, app):
        """Test parsing cover art data"""
        with app.app_context():
            service = MusicBrainzService()
            
            image_data = {
                'image': 'https://example.com/image.jpg',
                'thumbnails': {
                    'large': 'https://example.com/large.jpg',
                    '500': 'https://example.com/500.jpg'
                },
                'types': ['Front'],
                'approved': True,
                'comment': 'Test cover'
            }
            
            parsed = service._parse_cover_art(image_data, 'test-release', 0)
            
            assert parsed is not None
            assert parsed['source'] == 'musicbrainz'
            assert parsed['release_id'] == 'test-release'
            assert parsed['is_front'] == True
            assert parsed['primary_type'] == 'Front'
            assert parsed['approved'] == True
    
    @patch('requests.get')
    def test_download_artwork_success(self, mock_get, app):
        """Test successful artwork download"""
        with app.app_context():
            # Mock successful download
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_content.return_value = [b'fake image data']
            mock_get.return_value = mock_response
            
            service = MusicBrainzService()
            
            artwork_info = {
                'image_url': 'https://example.com/test.jpg'
            }
            
            result = service.download_artwork(artwork_info)
            
            assert result['success'] == True
            assert os.path.exists(result['local_path'])
            assert result['file_size'] > 0
            
            # Cleanup
            os.unlink(result['local_path'])
    
    @patch('requests.get')
    def test_download_artwork_error(self, mock_get, app):
        """Test artwork download with network error"""
        with app.app_context():
            mock_get.side_effect = requests.RequestException("Download failed")
            
            service = MusicBrainzService()
            
            artwork_info = {
                'image_url': 'https://example.com/test.jpg'
            }
            
            with pytest.raises(MusicBrainzError):
                service.download_artwork(artwork_info)
    
    @patch('musicbrainzngs.search_releases')
    @patch('requests.get')
    def test_search_and_get_artwork_workflow(self, mock_requests, mock_search, app, 
                                           mock_musicbrainz_response, mock_coverart_response):
        """Test complete workflow from search to artwork download"""
        with app.app_context():
            # Mock MusicBrainz search
            mock_search.return_value = mock_musicbrainz_response
            
            # Mock Cover Art Archive responses
            def mock_get_side_effect(url, **kwargs):
                mock_response = Mock()
                if 'coverartarchive.org' in url:
                    mock_response.status_code = 200
                    mock_response.json.return_value = mock_coverart_response
                else:
                    # Mock image download
                    mock_response.status_code = 200
                    mock_response.iter_content.return_value = [b'fake image data']
                return mock_response
            
            mock_requests.side_effect = mock_get_side_effect
            
            service = MusicBrainzService()
            service.rate_limit_delay = 0
            
            artwork_options = service.search_and_get_artwork('Test Artist', 'Test Song')
            
            assert len(artwork_options) > 0
            assert all('release_title' in art for art in artwork_options)
            assert all('release_artist' in art for art in artwork_options)
    
    @patch('musicbrainzngs.search_releases')
    def test_search_and_get_artwork_no_releases(self, mock_search, app):
        """Test workflow when no releases are found"""
        with app.app_context():
            mock_search.return_value = {'release-list': []}
            
            service = MusicBrainzService()
            service.rate_limit_delay = 0
            
            artwork_options = service.search_and_get_artwork('Unknown', 'Unknown')
            
            assert len(artwork_options) == 0
    
    def test_rate_limiting(self, app):
        """Test rate limiting functionality"""
        with app.app_context():
            service = MusicBrainzService()
            service.rate_limit_delay = 0.1  # Short delay for testing
            
            # First call should be immediate
            start_time = service.last_request_time
            service._rate_limit()
            
            # Second call should be delayed
            import time
            time.sleep(0.05)  # Sleep less than rate limit
            service._rate_limit()
            
            # Should have been delayed
            assert service.last_request_time > start_time
    
    @patch('musicbrainzngs.search_artists')
    def test_connection_test_success(self, mock_search, app):
        """Test successful connection test"""
        with app.app_context():
            mock_search.return_value = {'artist-list': []}
            
            service = MusicBrainzService()
            success, message = service.test_connection()
            
            assert success == True
            assert 'successful' in message.lower()
    
    @patch('musicbrainzngs.search_artists')
    def test_connection_test_failure(self, mock_search, app):
        """Test connection test failure"""
        with app.app_context():
            mock_search.side_effect = Exception("Connection failed")
            
            service = MusicBrainzService()
            success, message = service.test_connection()
            
            assert success == False
            assert 'Connection failed' in message


if __name__ == '__main__':
    pytest.main([__file__])
