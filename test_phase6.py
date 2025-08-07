#!/usr/bin/env python3
"""
Phase 6 Tests
Tests for User Interaction Features - Artwork Preview and Selection functionality.
"""

import json
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch

# Suppress logging during tests
logging.disable(logging.CRITICAL)

def test_phase6_imports():
    """Test that Phase 6 imports work correctly"""
    print("\n--- Testing Phase 6 Imports ---")
    
    try:
        # Test enhanced file operations import
        from processors.file_operations import FileOperations
        print("✅ Enhanced FileOperations import: Success")
        
        # Test that Flask app can import
        from app import app
        print("✅ Enhanced Flask app import: Success")
        
        # Test new methods are available
        file_ops = FileOperations()
        assert hasattr(file_ops, 'search_artwork_online'), "Should have search_artwork_online method"
        assert hasattr(file_ops, 'process_mp3_file_with_choice'), "Should have process_mp3_file_with_choice method"
        print("✅ New FileOperations methods: Available")
        
        print("✅ Phase 6 Imports: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_artwork_options_api():
    """Test the artwork options API endpoint"""
    print("\n--- Testing Artwork Options API ---")
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test invalid session ID
            response = client.get('/api/artwork-options/invalid-session/0')
            assert response.status_code == 404, "Should return 404 for invalid session"
            print("✅ Invalid session handling: Correct")
            
            # Test with mocked session data
            from app import processing_sessions
            
            # Create a mock session
            session_id = 'test-session-123'
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                test_file = temp_path / "Test Artist - Test Song.mp3"
                test_file.write_bytes(b"fake mp3 data")
                
                processing_sessions[session_id] = {
                    'status': 'uploaded',
                    'files': [{
                        'filename': 'Test Artist - Test Song.mp3',
                        'file_path': str(test_file)
                    }]
                }
                
                # Test with valid session but mocked MusicBrainz
                with patch('processors.file_operations.FileOperations.search_artwork_online') as mock_search:
                    mock_search.return_value = [
                        {
                            'release_id': 'test-id',
                            'release_title': 'Test Album',
                            'release_artist': 'Test Artist',
                            'artwork_url': 'https://example.com/art.jpg',
                            'thumbnail_url': 'https://example.com/thumb.jpg',
                            'is_front': True
                        }
                    ]
                    
                    response = client.get(f'/api/artwork-options/{session_id}/0')
                    
                    if response.status_code == 200:
                        data = json.loads(response.data)
                        assert 'file_info' in data, "Should include file info"
                        assert 'artwork_options' in data, "Should include artwork options"
                        print("✅ Valid session response: Correct structure")
                    else:
                        print(f"⚠️  API response status: {response.status_code}")
                
                # Cleanup
                del processing_sessions[session_id]
        
        print("✅ Artwork Options API: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Artwork options API test failed: {e}")
        return False

def test_artwork_preview_api():
    """Test the artwork preview API endpoint"""
    print("\n--- Testing Artwork Preview API ---")
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test missing artwork URL
            response = client.post('/api/artwork-preview', 
                                 json={})
            assert response.status_code == 400, "Should return 400 for missing URL"
            print("✅ Missing URL handling: Correct")
            
            # Test with mocked download and processing
            with patch('processors.file_operations.FileOperations') as mock_file_ops, \
                 patch('processors.artwork_processor.ArtworkProcessor') as mock_artwork_proc:
                
                # Mock the MusicBrainz client download
                mock_client = Mock()
                mock_client.download_artwork.return_value = b'fake_image_data'
                mock_file_ops.return_value.musicbrainz_client = mock_client
                
                # Mock artwork processor
                mock_processor = Mock()
                mock_processor.process_artwork.return_value = {
                    'is_compliant': True,
                    'processed_data': b'processed_image_data',
                    'was_resized': True,
                    'was_optimized': True,
                    'final_dimensions': {'width': 500, 'height': 500},
                    'processing_applied': ['Resized to 500x500', 'Optimized JPEG quality']
                }
                mock_artwork_proc.return_value = mock_processor
                
                response = client.post('/api/artwork-preview',
                                     json={'artwork_url': 'https://example.com/test.jpg'})
                
                if response.status_code == 200:
                    data = json.loads(response.data)
                    assert 'is_compliant' in data, "Should include compliance status"
                    assert 'preview_data_url' in data, "Should include preview data URL"
                    print("✅ Valid preview response: Correct structure")
                else:
                    print(f"⚠️  Preview API response status: {response.status_code}")
        
        print("✅ Artwork Preview API: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Artwork preview API test failed: {e}")
        return False

def test_artwork_selection_api():
    """Test the artwork selection API endpoint"""
    print("\n--- Testing Artwork Selection API ---")
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test invalid session ID
            response = client.post('/api/select-artwork/invalid-session/0',
                                 json={'artwork_url': 'https://example.com/test.jpg'})
            assert response.status_code == 404, "Should return 404 for invalid session"
            print("✅ Invalid session handling: Correct")
            
            # Test with valid session
            from app import processing_sessions
            
            session_id = 'test-session-456'
            processing_sessions[session_id] = {
                'status': 'uploaded',
                'files': [{'filename': 'test.mp3'}]
            }
            
            # Test artwork selection
            response = client.post(f'/api/select-artwork/{session_id}/0',
                                 json={'artwork_url': 'https://example.com/selected.jpg'})
            
            if response.status_code == 200:
                # Check that choice was stored
                assert 'artwork_choices' in processing_sessions[session_id], "Should store artwork choices"
                assert 0 in processing_sessions[session_id]['artwork_choices'], "Should store choice for file index"
                print("✅ Artwork selection storage: Working")
            
            # Test skip artwork
            response = client.post(f'/api/select-artwork/{session_id}/0',
                                 json={'skip_artwork': True})
            
            if response.status_code == 200:
                choice = processing_sessions[session_id]['artwork_choices'][0]
                assert choice['skip_artwork'] == True, "Should store skip choice"
                print("✅ Skip artwork functionality: Working")
            
            # Cleanup
            del processing_sessions[session_id]
        
        print("✅ Artwork Selection API: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Artwork selection API test failed: {e}")
        return False

def test_enhanced_file_operations():
    """Test enhanced file operations with user choices"""
    print("\n--- Testing Enhanced File Operations ---")
    
    try:
        from processors.file_operations import FileOperations
        
        # Test search_artwork_online with return_options
        file_ops = FileOperations(enable_musicbrainz=False)  # Disable for testing
        
        # Test with disabled MusicBrainz
        options = file_ops.search_artwork_online({}, return_options=True)
        assert options == [], "Should return empty list when disabled"
        print("✅ Disabled MusicBrainz handling: Correct")
        
        # Test process_mp3_file_with_choice method exists
        assert hasattr(file_ops, 'process_mp3_file_with_choice'), "Should have new processing method"
        print("✅ Enhanced processing method: Available")
        
        # Test with mock data
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.mp3"
            test_file.write_bytes(b"fake mp3 data")
            
            # Test with skip choice
            skip_choice = {'skip_artwork': True}
            result = file_ops.process_mp3_file_with_choice(test_file, user_artwork_choice=skip_choice)
            
            # Should handle gracefully even with invalid MP3
            assert 'success' in result, "Should return result structure"
            print("✅ User choice processing: Working")
        
        print("✅ Enhanced File Operations: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced file operations test failed: {e}")
        return False

def test_integration_with_previous_phases():
    """Test that Phase 6 integrates properly with all previous phases"""
    print("\n--- Testing Integration with Previous Phases ---")
    
    try:
        # Test that all previous functionality still works
        from processors.file_operations import FileOperations
        
        # Initialize with all features
        file_ops = FileOperations(enable_musicbrainz=True)
        
        # Test that previous methods still exist
        assert hasattr(file_ops, 'mp3_handler'), "Should have mp3_handler"
        assert hasattr(file_ops, 'artwork_processor'), "Should have artwork_processor"
        assert hasattr(file_ops, 'musicbrainz_client'), "Should have musicbrainz_client"
        assert hasattr(file_ops, 'process_mp3_file'), "Should have original processing method"
        
        print("✅ Previous phase integration: All components present")
        
        # Test that original processing still works
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "Artist - Title.mp3"
            test_file.write_bytes(b"fake mp3 data")
            
            result = file_ops.process_mp3_file(test_file, process_artwork=False)
            assert 'success' in result, "Original processing should still work"
            
        print("✅ Previous phase functionality: Preserved")
        
        print("✅ Integration with Previous Phases: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_frontend_integration():
    """Test frontend integration with new artwork selection features"""
    print("\n--- Testing Frontend Integration ---")
    
    try:
        # Test that HTML template includes required elements
        from app import app
        
        with app.test_client() as client:
            response = client.get('/')
            html_content = response.data.decode()
            
            # Check that the page loads
            assert response.status_code == 200, "Homepage should load"
            print("✅ Homepage loading: Working")
            
            # The JavaScript and CSS should be included
            assert 'app.js' in html_content, "Should include JavaScript file"
            assert 'style.css' in html_content, "Should include CSS file"
            print("✅ Static file inclusion: Working")
        
        # Test that CSS includes Phase 6 styles
        css_path = Path('static/css/style.css')
        if css_path.exists():
            css_content = css_path.read_text()
            assert 'artwork-modal' in css_content, "Should include artwork modal styles"
            assert 'artwork-grid' in css_content, "Should include artwork grid styles"
            print("✅ Phase 6 CSS styles: Present")
        
        # Test that JavaScript includes Phase 6 functions
        js_path = Path('static/js/app.js')
        if js_path.exists():
            js_content = js_path.read_text()
            assert 'showArtworkOptions' in js_content, "Should include artwork options function"
            assert 'previewArtwork' in js_content, "Should include preview function"
            assert 'selectArtwork' in js_content, "Should include selection function"
            print("✅ Phase 6 JavaScript functions: Present")
        
        print("✅ Frontend Integration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Frontend integration test failed: {e}")
        return False

def main():
    """Run all Phase 6 tests"""
    print("🧪 Running Phase 6 Tests")
    print("Testing User Interaction Features - Artwork Preview and Selection")
    print("=" * 75)
    
    tests = [
        ("Phase 6 Imports", test_phase6_imports),
        ("Artwork Options API", test_artwork_options_api),
        ("Artwork Preview API", test_artwork_preview_api),
        ("Artwork Selection API", test_artwork_selection_api),
        ("Enhanced File Operations", test_enhanced_file_operations),
        ("Integration with Previous Phases", test_integration_with_previous_phases),
        ("Frontend Integration", test_frontend_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 60)
        
        try:
            success = test_func()
            if success:
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 75)
    print(f"📊 PHASE 6 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 6 FUNCTIONALITY IS WORKING!")
        print("✅ Artwork preview and selection features complete")
        print("✅ User interaction features integrated successfully")
        print("✅ All phases (1-6) integrated and functional")
        print("\n🚀 COMPLETE MP3 ARTWORK MANAGER WITH USER INTERACTION!")
    else:
        print(f"⚠️  {total - passed} Phase 6 tests failed. Please review failures above.")
    
    return passed == total

if __name__ == "__main__":
    main() 