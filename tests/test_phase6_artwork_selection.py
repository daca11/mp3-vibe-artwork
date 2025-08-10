"""
Unit tests for Phase 6: Artwork Selection Interface
"""
import pytest
import tempfile
import os
from app import create_app
from app.models.file_queue import FileQueue


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
def sample_file_with_artwork(app):
    """Create a sample file with multiple artwork options"""
    with app.app_context():
        from app.models.file_queue import get_queue
        from PIL import Image
        
        queue = get_queue()
        
        # Create a test file
        queued_file = queue.add_file(
            filename='test_song.mp3',
            file_path='/tmp/test_song.mp3',
            size=1024000,
            mime_type='audio/mpeg'
        )
        
        # Create temporary artwork files
        temp_dir = app.config['TEMP_FOLDER']
        
        # Oversized artwork (600x600)
        img_large = Image.new('RGB', (600, 600), color='red')
        large_artwork_path = os.path.join(temp_dir, 'embedded_artwork.jpg')
        img_large.save(large_artwork_path, 'JPEG')
        
        # MusicBrainz artwork will now be a URL
        musicbrainz_artwork_url = 'https://coverartarchive.org/release/some-release-id/front-500.jpg'

        # Add embedded artwork
        queued_file.add_artwork_option(
            source='embedded',
            image_path=large_artwork_path,
            dimensions={'width': 600, 'height': 600},
            file_size=os.path.getsize(large_artwork_path),
            metadata={'format': 'JPEG', 'description': 'Front cover'}
        )
        
        # Add MusicBrainz artwork
        queued_file.add_artwork_option(
            source='musicbrainz',
            image_path=musicbrainz_artwork_url,
            dimensions=None,
            file_size=None,
            metadata={
                'release_title': 'Test Album',
                'release_artist': 'Test Artist',
                'primary_type': 'Front',
                'source_url': musicbrainz_artwork_url
            }
        )
        
        queue._save_queue()
        
        yield queued_file.id
        
        # Cleanup
        queue.remove_file(queued_file.id)
        try:
            os.unlink(large_artwork_path)
        except OSError:
            pass


class TestArtworkEndpoints:
    """Test artwork API endpoints"""
    
    def test_artwork_selection_page_loads(self, client):
        """Test that artwork selection page loads"""
        response = client.get('/artwork-selection')
        assert response.status_code == 200
        assert b'Artwork Selection' in response.data
    
    def test_get_artwork_options_nonexistent_file(self, client):
        """Test getting artwork options for non-existent file"""
        response = client.get('/api/artwork/nonexistent-id')
        assert response.status_code == 404
        data = response.get_json()
        assert 'File not found' in data['error']
    
    def test_get_artwork_options_success(self, client, sample_file_with_artwork):
        """Test successfully getting artwork options"""
        response = client.get(f'/api/artwork/{sample_file_with_artwork}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['file_id'] == sample_file_with_artwork
        assert 'artwork_options' in data
        assert 'total_options' in data
        assert data['total_options'] >= 2  # Should have embedded + musicbrainz
        
        musicbrainz_art = next((art for art in data['artwork_options'] if art['source'] == 'musicbrainz'), None)
        assert musicbrainz_art is not None
        assert 'image_url' in musicbrainz_art
        assert musicbrainz_art['preview_url'] == musicbrainz_art['image_url']

    def test_get_artwork_preview_nonexistent_file(self, client):
        """Test getting artwork preview for non-existent file"""
        response = client.get('/api/artwork/nonexistent-id/preview/artwork-id')
        assert response.status_code == 404
    
    def test_get_artwork_preview_nonexistent_artwork(self, client, sample_file_with_artwork):
        """Test getting preview for non-existent artwork"""
        response = client.get(f'/api/artwork/{sample_file_with_artwork}/preview/nonexistent-artwork')
        assert response.status_code == 404

    def test_get_artwork_preview_success(self, client, sample_file_with_artwork, app):
        """Test getting artwork preview for both embedded and musicbrainz"""
        with app.app_context():
            response = client.get(f'/api/artwork/{sample_file_with_artwork}')
            data = response.get_json()
            
            # Test embedded artwork preview
            embedded_art = next((art for art in data['artwork_options'] if art['source'] == 'embedded'), None)
            assert embedded_art is not None
            preview_response = client.get(f"/api/artwork/{sample_file_with_artwork}/preview/{embedded_art['id']}")
            assert preview_response.status_code == 200
            assert preview_response.mimetype == 'image/jpeg'

            # Test MusicBrainz artwork preview (should redirect)
            musicbrainz_art = next((art for art in data['artwork_options'] if art['source'] == 'musicbrainz'), None)
            assert musicbrainz_art is not None
            preview_response = client.get(f"/api/artwork/{sample_file_with_artwork}/preview/{musicbrainz_art['id']}")
            assert preview_response.status_code == 302 # Found (redirect)
            assert 'location' in preview_response.headers
            assert preview_response.headers['location'] == musicbrainz_art['image_url']

    def test_select_artwork_no_data(self, client, sample_file_with_artwork):
        """Test selecting artwork without providing artwork_id"""
        response = client.post(f'/api/artwork/{sample_file_with_artwork}/select',
                             json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'No artwork_id provided' in data['error']
    
    def test_select_artwork_nonexistent_file(self, client):
        """Test selecting artwork for non-existent file"""
        response = client.post('/api/artwork/nonexistent-id/select',
                             json={'artwork_id': 'some-id'})
        assert response.status_code == 404
    
    def test_select_artwork_nonexistent_artwork(self, client, sample_file_with_artwork):
        """Test selecting non-existent artwork"""
        response = client.post(f'/api/artwork/{sample_file_with_artwork}/select',
                             json={'artwork_id': 'nonexistent-artwork'})
        assert response.status_code == 404
    
    def test_select_artwork_success(self, client, sample_file_with_artwork, app):
        """Test successfully selecting artwork"""
        with app.app_context():
            # First get the available artwork options
            response = client.get(f'/api/artwork/{sample_file_with_artwork}')
            assert response.status_code == 200
            
            data = response.get_json()
            artwork_options = data['artwork_options']
            assert len(artwork_options) > 0
            
            # Select the first artwork option
            artwork_id = artwork_options[0]['id']
            
            response = client.post(f'/api/artwork/{sample_file_with_artwork}/select',
                                 json={'artwork_id': artwork_id})
            assert response.status_code == 200
            
            selection_data = response.get_json()
            assert selection_data['selected_artwork_id'] == artwork_id
            assert 'selected_artwork' in selection_data
    
    def test_select_artwork_with_optimization(self, client, sample_file_with_artwork, app):
        """Test that oversized artwork is optimized upon selection"""
        with app.app_context():
            from app.models.file_queue import get_queue
            
            # Get the file and its artwork options
            response = client.get(f'/api/artwork/{sample_file_with_artwork}')
            data = response.get_json()
            
            # Find the oversized artwork (600x600 in fixture, which is embedded)
            oversized_artwork = next(
                (art for art in data['artwork_options'] if art.get('dimensions') and art['dimensions']['width'] > 500), 
                None
            )
            assert oversized_artwork is not None, "Oversized artwork not found in test setup"
            assert oversized_artwork['source'] == 'embedded'
            
            # Select the oversized artwork
            artwork_id = oversized_artwork['id']
            response = client.post(f'/api/artwork/{sample_file_with_artwork}/select',
                                 json={'artwork_id': artwork_id})
            
            assert response.status_code == 200, f"API call failed with status {response.status_code}: {response.get_data(as_text=True)}"
            
            # Verify that the artwork was optimized and selected
            queue = get_queue()
            updated_file = queue.get_file(sample_file_with_artwork)
            selected_art = updated_file.selected_artwork
            
            assert selected_art is not None, "Artwork was not selected"
            assert selected_art['id'] == artwork_id
            
            # Verify that the original artwork is selected and not optimized at this stage
            assert 'optimized_path' not in selected_art or selected_art['optimized_path'] is None
            assert selected_art['image_path'] is not None

    def test_compare_artwork_nonexistent_file(self, client):
        """Test artwork comparison for non-existent file"""
        response = client.get('/api/artwork/nonexistent-id/compare')
        assert response.status_code == 404
    
    def test_compare_artwork_success(self, client, sample_file_with_artwork):
        """Test successful artwork comparison"""
        response = client.get(f'/api/artwork/{sample_file_with_artwork}/compare')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'file_info' in data
        assert 'artwork_options' in data
        assert data['file_info']['id'] == sample_file_with_artwork
        
        # Check that artwork options have detailed information
        for artwork in data['artwork_options']:
            assert 'preview_url' in artwork
            assert 'thumbnail_url' in artwork
            assert 'dimensions' in artwork
            assert 'file_size' in artwork
            assert 'source' in artwork
            if artwork['source'] == 'musicbrainz':
                assert artwork['preview_url'].startswith('http')
    
    def test_bulk_select_no_data(self, client):
        """Test bulk selection without data"""
        response = client.post('/api/artwork/bulk-select', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'No selections provided' in data['error']
    
    def test_bulk_select_invalid_data(self, client):
        """Test bulk selection with invalid data"""
        response = client.post('/api/artwork/bulk-select', 
                             json={'selections': [{'file_id': 'invalid'}]})
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['successful_count'] == 0
        assert len(data['results']) == 1
        assert data['results'][0]['success'] == False
    
    def test_bulk_select_success(self, client, sample_file_with_artwork, app):
        """Test successful bulk selection"""
        with app.app_context():
            # Get artwork options first
            response = client.get(f'/api/artwork/{sample_file_with_artwork}')
            data = response.get_json()
            artwork_id = data['artwork_options'][0]['id']
            
            # Perform bulk selection
            selections = [{'file_id': sample_file_with_artwork, 'artwork_id': artwork_id}]
            response = client.post('/api/artwork/bulk-select',
                                 json={'selections': selections})
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['successful_count'] == 1
            assert data['total_count'] == 1
            assert data['results'][0]['success'] == True


class TestArtworkSelectionUI:
    """Test artwork selection user interface functionality"""
    
    def test_artwork_selection_template_renders(self, client):
        """Test that artwork selection template renders properly"""
        response = client.get('/artwork-selection?file_id=test')
        assert response.status_code == 200
        
        # Check for key UI elements
        assert b'Artwork Selection' in response.data
        assert b'comparison-view' in response.data
        assert b'apply-selection' in response.data
        assert b'back-to-queue' in response.data
    
    def test_artwork_selection_includes_required_scripts(self, client):
        """Test that required JavaScript is included"""
        response = client.get('/artwork-selection')
        assert response.status_code == 200
        
        # Check for key JavaScript functionality
        assert b'ArtworkSelector' in response.data
        assert b'loadArtworkOptions' in response.data
        assert b'applySelection' in response.data
    
    def test_artwork_selection_includes_styling(self, client):
        """Test that required CSS styling is included"""
        response = client.get('/artwork-selection')
        assert response.status_code == 200
        
        # Check for key CSS classes
        assert b'artwork-card' in response.data
        assert b'comparison-view' in response.data
        assert b'artwork-preview' in response.data


if __name__ == '__main__':
    pytest.main([__file__])
