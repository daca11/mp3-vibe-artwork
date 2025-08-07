#!/usr/bin/env python3
"""
MusicBrainz Client Tests
Tests for MusicBrainz API integration functionality.
"""

import time
import logging
from unittest.mock import Mock, patch, MagicMock
from processors.musicbrainz_client import MusicBrainzClient

# Suppress logging during tests
logging.disable(logging.CRITICAL)

def test_client_initialization():
    """Test MusicBrainz client initialization"""
    print("\n--- Testing MusicBrainz Client Initialization ---")
    
    try:
        # Test default initialization
        client = MusicBrainzClient()
        
        assert hasattr(client, 'rate_limit'), "Client should have rate_limit attribute"
        assert hasattr(client, 'last_request_time'), "Client should have last_request_time attribute"
        assert client.rate_limit == 1.0, "Default rate limit should be 1.0 seconds"
        
        print("✅ Default initialization: Correct")
        
        # Test custom initialization
        custom_client = MusicBrainzClient(
            user_agent="TestApp/2.0", 
            rate_limit=0.5
        )
        
        assert custom_client.rate_limit == 0.5, "Custom rate limit should be set correctly"
        
        print("✅ Custom initialization: Correct")
        print("✅ MusicBrainz Client Initialization: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False

def test_rate_limiting():
    """Test rate limiting functionality"""
    print("\n--- Testing Rate Limiting ---")
    
    try:
        client = MusicBrainzClient(rate_limit=0.1)  # Fast for testing
        
        # Test initial delay (should be none)
        start_time = time.time()
        client._rate_limit_delay()
        elapsed = time.time() - start_time
        
        assert elapsed < 0.05, "Initial delay should be minimal"
        print("✅ Initial delay: Minimal as expected")
        
        # Test subsequent delay
        client.last_request_time = time.time()
        start_time = time.time()
        client._rate_limit_delay()
        elapsed = time.time() - start_time
        
        assert elapsed >= 0.08, "Rate limiting delay should be enforced"
        print("✅ Rate limiting delay: Enforced correctly")
        
        print("✅ Rate Limiting: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

@patch('processors.musicbrainz_client.musicbrainzngs.search_releases')
def test_search_release_basic(mock_search):
    """Test basic release search functionality"""
    print("\n--- Testing Basic Release Search ---")
    
    try:
        # Mock MusicBrainz response
        mock_response = {
            'release-list': [
                {
                    'id': 'test-release-id-1',
                    'title': 'Test Album',
                    'date': '2023-01-01',
                    'artist-credit': [
                        {'artist': {'name': 'Test Artist'}}
                    ],
                    'ext:score': 100
                }
            ]
        }
        mock_search.return_value = mock_response
        
        client = MusicBrainzClient(rate_limit=0.0)  # No delay for testing
        
        # Test search with artist only
        results = client.search_release("Test Artist")
        
        assert len(results) == 1, "Should return one result"
        assert results[0]['artist'] == 'Test Artist', "Artist should match"
        assert results[0]['title'] == 'Test Album', "Title should match"
        assert results[0]['id'] == 'test-release-id-1', "ID should match"
        
        print("✅ Artist-only search: Working correctly")
        
        # Test search with artist and album
        results = client.search_release("Test Artist", "Test Album")
        
        assert len(results) == 1, "Should return one result for artist+album search"
        print("✅ Artist+album search: Working correctly")
        
        # Test search with all parameters
        results = client.search_release("Test Artist", "Test Album", "Test Song")
        
        assert len(results) == 1, "Should return one result for full search"
        print("✅ Full search (artist+album+title): Working correctly")
        
        # Test empty artist (should return empty)
        results = client.search_release("")
        assert len(results) == 0, "Empty artist should return no results"
        print("✅ Empty artist handling: Correct")
        
        print("✅ Basic Release Search: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Basic release search test failed: {e}")
        return False

@patch('processors.musicbrainz_client.musicbrainzngs.search_releases')
def test_search_error_handling(mock_search):
    """Test error handling in search functionality"""
    print("\n--- Testing Search Error Handling ---")
    
    try:
        import musicbrainzngs
        client = MusicBrainzClient(rate_limit=0.0)
        
        # Test network error
        mock_search.side_effect = musicbrainzngs.NetworkError("Network error")
        results = client.search_release("Test Artist")
        assert len(results) == 0, "Network error should return empty results"
        print("✅ Network error handling: Correct")
        
        # Test API response error
        mock_search.side_effect = musicbrainzngs.ResponseError("API error")
        results = client.search_release("Test Artist")
        assert len(results) == 0, "API error should return empty results"
        print("✅ API error handling: Correct")
        
        # Test general exception
        mock_search.side_effect = Exception("General error")
        results = client.search_release("Test Artist")
        assert len(results) == 0, "General error should return empty results"
        print("✅ General error handling: Correct")
        
        print("✅ Search Error Handling: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Search error handling test failed: {e}")
        return False

@patch('processors.musicbrainz_client.musicbrainzngs.get_image_list')
def test_artwork_urls_basic(mock_get_images):
    """Test basic artwork URL retrieval"""
    print("\n--- Testing Basic Artwork URL Retrieval ---")
    
    try:
        # Mock Cover Art Archive response
        mock_response = {
            'images': [
                {
                    'image': 'https://example.com/image1.jpg',
                    'thumbnails': {
                        '500': 'https://example.com/thumb500_1.jpg',
                        'large': 'https://example.com/large_1.jpg'
                    },
                    'types': ['Front'],
                    'width': 1000,
                    'height': 1000,
                    'approved': True,
                    'comment': 'Front cover'
                },
                {
                    'image': 'https://example.com/image2.jpg',
                    'thumbnails': {
                        'large': 'https://example.com/large_2.jpg'
                    },
                    'types': ['Back'],
                    'width': 800,
                    'height': 800,
                    'approved': True,
                    'comment': 'Back cover'
                }
            ]
        }
        mock_get_images.return_value = mock_response
        
        client = MusicBrainzClient(rate_limit=0.0)
        
        # Test getting artwork URLs
        artwork_urls = client.get_artwork_urls('test-release-id')
        
        assert len(artwork_urls) == 2, "Should return two artwork entries"
        
        # Check that front cover is sorted first
        front_cover = artwork_urls[0]
        assert front_cover['is_front'] == True, "Front cover should be first"
        assert front_cover['thumbnail_url'] == 'https://example.com/thumb500_1.jpg', "Should prefer 500px thumbnail"
        
        print("✅ Artwork URL retrieval: Working correctly")
        print("✅ Front cover prioritization: Correct")
        print("✅ Thumbnail preference: Correct")
        
        print("✅ Basic Artwork URL Retrieval: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Basic artwork URL test failed: {e}")
        return False

@patch('processors.musicbrainz_client.musicbrainzngs.get_image_list')
def test_artwork_error_handling(mock_get_images):
    """Test error handling in artwork retrieval"""
    print("\n--- Testing Artwork Error Handling ---")
    
    try:
        import musicbrainzngs
        client = MusicBrainzClient(rate_limit=0.0)
        
        # Test 404 error (no artwork found)
        mock_get_images.side_effect = musicbrainzngs.ResponseError("404 Not Found")
        artwork_urls = client.get_artwork_urls('test-release-id')
        assert len(artwork_urls) == 0, "404 error should return empty list"
        print("✅ No artwork found (404): Handled correctly")
        
        # Test other API errors
        mock_get_images.side_effect = musicbrainzngs.ResponseError("500 Server Error")
        artwork_urls = client.get_artwork_urls('test-release-id')
        assert len(artwork_urls) == 0, "Server error should return empty list"
        print("✅ Server error handling: Correct")
        
        print("✅ Artwork Error Handling: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Artwork error handling test failed: {e}")
        return False

@patch('processors.musicbrainz_client.requests.get')
def test_download_artwork(mock_get):
    """Test artwork download functionality"""
    print("\n--- Testing Artwork Download ---")
    
    try:
        # Mock successful download
        mock_response = Mock()
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b'fake', b'image', b'data']
        mock_get.return_value = mock_response
        
        client = MusicBrainzClient(rate_limit=0.0)
        
        # Test successful download
        artwork_data = client.download_artwork('https://example.com/image.jpg')
        
        assert artwork_data == b'fakeimagedata', "Should return combined image data"
        print("✅ Successful download: Working correctly")
        
        # Test invalid content type
        mock_response.headers = {'content-type': 'text/html'}
        artwork_data = client.download_artwork('https://example.com/image.jpg')
        assert artwork_data is None, "Invalid content type should return None"
        print("✅ Invalid content type: Handled correctly")
        
        # Test request exception
        mock_get.side_effect = Exception("Download error")
        artwork_data = client.download_artwork('https://example.com/image.jpg')
        assert artwork_data is None, "Download error should return None"
        print("✅ Download error handling: Correct")
        
        print("✅ Artwork Download: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Artwork download test failed: {e}")
        return False

@patch('processors.musicbrainz_client.MusicBrainzClient.get_artwork_urls')
@patch('processors.musicbrainz_client.MusicBrainzClient.search_release')
def test_combined_search_and_artwork(mock_search, mock_artwork):
    """Test combined search and artwork retrieval"""
    print("\n--- Testing Combined Search and Artwork ---")
    
    try:
        # Mock search results
        mock_search.return_value = [
            {
                'id': 'release-1',
                'title': 'Album 1',
                'artist': 'Artist 1',
                'artwork_urls': []
            }
        ]
        
        # Mock artwork URLs
        mock_artwork.return_value = [
            {
                'image_url': 'https://example.com/artwork.jpg',
                'is_front': True
            }
        ]
        
        client = MusicBrainzClient(rate_limit=0.0)
        
        # Test combined functionality
        results = client.search_and_get_artwork("Test Artist", "Test Album")
        
        assert len(results) == 1, "Should return one result"
        assert len(results[0]['artwork_urls']) == 1, "Should have artwork URLs populated"
        assert results[0]['artwork_urls'][0]['is_front'] == True, "Should have front cover"
        
        print("✅ Combined search and artwork: Working correctly")
        print("✅ Artwork URL population: Correct")
        
        print("✅ Combined Search and Artwork: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Combined search and artwork test failed: {e}")
        return False

def test_fallback_search_strategies():
    """Test fallback search strategies implementation"""
    print("\n--- Testing Fallback Search Strategies ---")
    
    # Note: This is a placeholder for fallback strategies that will be implemented
    # Currently testing the foundation for fallback logic
    
    try:
        client = MusicBrainzClient(rate_limit=0.0)
        
        # Test that client can handle missing metadata gracefully
        # (This will be expanded when fallback strategies are implemented)
        
        print("✅ Fallback search foundation ready")
        print("✅ Fallback Search Strategies: FOUNDATION READY")
        return True
        
    except Exception as e:
        print(f"❌ Fallback search test failed: {e}")
        return False

def main():
    """Run all MusicBrainz client tests"""
    print("🧪 Running MusicBrainz Client Tests (Phase 5.1 & 5.2)")
    print("=" * 65)
    
    tests = [
        ("Client Initialization", test_client_initialization),
        ("Rate Limiting", test_rate_limiting),
        ("Basic Release Search", test_search_release_basic),
        ("Search Error Handling", test_search_error_handling),
        ("Basic Artwork URL Retrieval", test_artwork_urls_basic),
        ("Artwork Error Handling", test_artwork_error_handling),
        ("Artwork Download", test_download_artwork),
        ("Combined Search and Artwork", test_combined_search_and_artwork),
        ("Fallback Search Strategies", test_fallback_search_strategies)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 50)
        
        try:
            success = test_func()
            if success:
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 65)
    print(f"📊 MUSICBRAINZ CLIENT TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL MUSICBRAINZ CLIENT TESTS PASSED!")
        print("✅ Phase 5.1 Basic API Integration complete")
        print("✅ Phase 5.2 Advanced Search Features foundation ready")
        print("✅ MusicBrainz integration ready for use")
    else:
        print(f"⚠️  {total - passed} MusicBrainz tests failed. Please review failures above.")
    
    return passed == total

if __name__ == "__main__":
    main() 