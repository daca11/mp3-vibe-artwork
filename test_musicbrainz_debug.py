#!/usr/bin/env python3
"""
MusicBrainz Debug Test
Test MusicBrainz integration with real-world scenarios to debug issues.
"""

import tempfile
import logging
from pathlib import Path
from processors.file_operations import FileOperations

# Enable logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_musicbrainz_with_fake_mp3():
    """Test MusicBrainz integration with a fake MP3 file"""
    print("🔍 Testing MusicBrainz integration with fake MP3...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a fake MP3 file with metadata in filename
        test_file = temp_path / "The Beatles - Yesterday.mp3"
        test_file.write_bytes(b"fake mp3 data for testing")
        
        print(f"Created test file: {test_file}")
        
        # Initialize file operations with MusicBrainz enabled
        file_ops = FileOperations(enable_musicbrainz=True)
        
        if not file_ops.enable_musicbrainz:
            print("❌ MusicBrainz is not enabled")
            return False
        
        print("✅ MusicBrainz client initialized")
        
        # Test metadata extraction
        metadata = file_ops.mp3_handler.extract_metadata(test_file)
        print(f"Extracted metadata: {metadata}")
        
        # Test filename parsing
        parsed_info = file_ops.parse_filename_for_metadata(test_file.name)
        print(f"Parsed filename info: {parsed_info}")
        
        # Test MusicBrainz search directly
        print("\n🎵 Testing MusicBrainz search...")
        artwork_result = file_ops.search_artwork_online(metadata, parsed_info)
        
        if artwork_result:
            print(f"✅ Found artwork: {len(artwork_result[0])} bytes, type: {artwork_result[1]}")
        else:
            print("⚠️  No artwork found or search failed")
        
        # Test complete processing pipeline
        print("\n🔄 Testing complete processing pipeline...")
        result = file_ops.process_mp3_file(test_file, process_artwork=True)
        
        print(f"Processing result: {result.get('success', False)}")
        print(f"Error: {result.get('error', 'None')}")
        print(f"Artwork info: {result.get('artwork_info', {})}")
        
        return True

def test_musicbrainz_search_params():
    """Test MusicBrainz search with different parameter combinations"""
    print("\n🔍 Testing MusicBrainz search parameters...")
    
    file_ops = FileOperations(enable_musicbrainz=True)
    
    if not file_ops.enable_musicbrainz:
        print("❌ MusicBrainz is not enabled")
        return False
    
    # Test different search scenarios
    test_cases = [
        {
            'name': 'Complete metadata',
            'metadata': {'artist': 'The Beatles', 'album': 'Help!', 'title': 'Yesterday'},
            'parsed_info': None
        },
        {
            'name': 'Artist and title only',
            'metadata': {'artist': 'The Beatles', 'album': None, 'title': 'Yesterday'},
            'parsed_info': None
        },
        {
            'name': 'Parsed filename only',
            'metadata': {'artist': None, 'album': None, 'title': None},
            'parsed_info': {'artist': 'The Beatles', 'title': 'Yesterday'}
        },
        {
            'name': 'No metadata',
            'metadata': {'artist': None, 'album': None, 'title': None},
            'parsed_info': None
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        result = file_ops.search_artwork_online(test_case['metadata'], test_case['parsed_info'])
        
        if result:
            print(f"✅ Found artwork: {len(result[0])} bytes")
        else:
            print("⚠️  No artwork found")
    
    return True

def main():
    """Run debug tests"""
    print("🧪 MusicBrainz Debug Tests")
    print("=" * 50)
    
    try:
        test_musicbrainz_with_fake_mp3()
        test_musicbrainz_search_params()
        print("\n✅ Debug tests completed")
    except Exception as e:
        print(f"\n❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 