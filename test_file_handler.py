#!/usr/bin/env python3
"""
Test Module for MP3 File Handler
Tests MP3 file detection, validation, metadata extraction, and artwork extraction.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from processors.file_handler import MP3FileHandler

def create_test_files():
    """Create test files for testing MP3 file detection"""
    test_dir = Path(tempfile.mkdtemp(prefix='mp3_test_'))
    
    # Create various test files with unique names to avoid case-sensitivity issues
    test_files = {
        'song1.mp3': b'ID3\x03\x00\x00\x00\x00\x00\x00',   # Lowercase extension
        'SONG2.MP3': b'ID3\x03\x00\x00\x00\x00\x00\x00',   # Uppercase extension  
        'Song3.Mp3': b'ID3\x03\x00\x00\x00\x00\x00\x00',   # Mixed case extension
        'test.txt': b'This is not an MP3 file',             # Text file
        'test.wav': b'RIFF\x00\x00\x00\x00WAVE',           # WAV file
        'no_extension': b'Some data without extension'      # No extension
    }
    
    for filename, content in test_files.items():
        file_path = test_dir / filename
        file_path.write_bytes(content)
    
    return test_dir

def test_mp3_file_detection():
    """Test MP3 file detection functionality"""
    print("Testing MP3 file detection...")
    
    handler = MP3FileHandler()
    test_dir = create_test_files()
    
    try:
        # Test directory scanning
        mp3_files = handler.detect_mp3_files(test_dir)
        mp3_filenames = [f.name for f in mp3_files]
        
        expected_mp3_files = {'song1.mp3', 'SONG2.MP3', 'Song3.Mp3'}
        found_mp3_files = set(mp3_filenames)
        
        if expected_mp3_files == found_mp3_files:
            print("✅ Directory scanning: Found all MP3 files with different case extensions")
        elif len(found_mp3_files) == 3 and all(f.lower().endswith('.mp3') for f in found_mp3_files):
            print("✅ Directory scanning: Found all MP3 files (case-insensitive filesystem)")
        else:
            print(f"❌ Directory scanning: Expected 3 MP3 files, found {len(found_mp3_files)}: {found_mp3_files}")
            return False
        
        # Test single file detection
        single_mp3 = test_dir / 'song1.mp3'
        single_result = handler.detect_mp3_files(single_mp3)
        
        if len(single_result) == 1 and single_result[0].name == 'song1.mp3':
            print("✅ Single file detection: Correctly identified MP3 file")
        else:
            print(f"❌ Single file detection: Expected 1 file, got {len(single_result)}")
            return False
        
        # Test non-MP3 file
        txt_file = test_dir / 'test.txt'
        txt_result = handler.detect_mp3_files(txt_file)
        
        if len(txt_result) == 0:
            print("✅ Non-MP3 file rejection: Correctly rejected .txt file")
        else:
            print(f"❌ Non-MP3 file rejection: Should reject .txt file, but found {len(txt_result)} files")
            return False
        
        # Test is_mp3_file method
        test_cases = [
            ('song1.mp3', True),
            ('SONG2.MP3', True),
            ('Song3.Mp3', True),
            ('test.txt', False),
            ('test.wav', False),
            ('no_extension', False)
        ]
        
        for filename, expected in test_cases:
            result = handler.is_mp3_file(test_dir / filename)
            if result == expected:
                print(f"✅ Extension check: {filename} -> {result}")
            else:
                print(f"❌ Extension check: {filename} expected {expected}, got {result}")
                return False
        
        # Test additional case variations that might not exist as files
        additional_cases = [
            ('virtual.mP3', True),
            ('virtual.MP4', False),
            ('virtual', False)
        ]
        
        for filename, expected in additional_cases:
            result = handler.is_mp3_file(filename)  # Test without creating file
            if result == expected:
                print(f"✅ Extension check (virtual): {filename} -> {result}")
            else:
                print(f"❌ Extension check (virtual): {filename} expected {expected}, got {result}")
                return False
        
        return True
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)

def test_error_handling():
    """Test error handling for invalid paths and permissions"""
    print("\nTesting error handling...")
    
    handler = MP3FileHandler()
    
    # Test non-existent path
    try:
        handler.detect_mp3_files('/non/existent/path')
        print("❌ Error handling: Should raise FileNotFoundError for non-existent path")
        return False
    except FileNotFoundError:
        print("✅ Error handling: Correctly raised FileNotFoundError for non-existent path")
    except Exception as e:
        print(f"❌ Error handling: Unexpected exception: {e}")
        return False
    
    # Test file validation
    test_cases = [
        ('/non/existent/file.mp3', False, "File does not exist"),
        ('test.txt', False, "does not have MP3 extension")
    ]
    
    # Create a temporary directory for testing
    test_dir = Path(tempfile.mkdtemp(prefix='mp3_error_test_'))
    
    try:
        # Create a non-MP3 file
        txt_file = test_dir / 'test.txt'
        txt_file.write_text('This is not an MP3')
        
        for file_path, expected_valid, expected_error_substring in test_cases:
            if not Path(file_path).is_absolute():
                file_path = test_dir / file_path
            
            is_valid, error_message = handler.validate_mp3_file(file_path)
            
            if is_valid == expected_valid:
                if not expected_valid and expected_error_substring in (error_message or ""):
                    print(f"✅ Validation: {Path(file_path).name} correctly identified as invalid")
                elif expected_valid:
                    print(f"✅ Validation: {Path(file_path).name} correctly identified as valid")
                else:
                    print(f"❌ Validation: {Path(file_path).name} error message doesn't contain expected text")
                    return False
            else:
                print(f"❌ Validation: {Path(file_path).name} expected valid={expected_valid}, got {is_valid}")
                return False
        
        return True
        
    finally:
        shutil.rmtree(test_dir)

def test_metadata_extraction():
    """Test metadata extraction with missing metadata"""
    print("\nTesting metadata extraction...")
    
    handler = MP3FileHandler()
    
    # Create a minimal test file (won't have real metadata, but tests graceful handling)
    test_dir = Path(tempfile.mkdtemp(prefix='mp3_metadata_test_'))
    
    try:
        test_file = test_dir / 'test.mp3'
        # Create a minimal file that looks like MP3 but has no real metadata
        test_file.write_bytes(b'ID3\x03\x00\x00\x00\x00\x00\x00')
        
        metadata = handler.extract_metadata(test_file)
        
        # Should return dict with None values for missing metadata
        expected_keys = {'artist', 'album', 'title', 'genre', 'year'}
        
        if set(metadata.keys()) == expected_keys:
            print("✅ Metadata extraction: Returns correct keys")
        else:
            print(f"❌ Metadata extraction: Expected keys {expected_keys}, got {set(metadata.keys())}")
            return False
        
        # All values should be None for this test file
        if all(value is None for value in metadata.values()):
            print("✅ Metadata extraction: Gracefully handles missing metadata")
        else:
            print(f"❌ Metadata extraction: Expected all None values, got {metadata}")
            return False
        
        return True
        
    finally:
        shutil.rmtree(test_dir)

def test_artwork_extraction():
    """Test artwork extraction with files that have no artwork"""
    print("\nTesting artwork extraction...")
    
    handler = MP3FileHandler()
    
    # Create a test file without artwork
    test_dir = Path(tempfile.mkdtemp(prefix='mp3_artwork_test_'))
    
    try:
        test_file = test_dir / 'test.mp3'
        # Create a minimal file that looks like MP3 but has no artwork
        test_file.write_bytes(b'ID3\x03\x00\x00\x00\x00\x00\x00')
        
        artwork = handler.extract_artwork(test_file)
        
        if artwork is None:
            print("✅ Artwork extraction: Correctly returns None for files without artwork")
        else:
            print(f"❌ Artwork extraction: Expected None, got {type(artwork)}")
            return False
        
        return True
        
    finally:
        shutil.rmtree(test_dir)

def test_file_info():
    """Test comprehensive file info gathering"""
    print("\nTesting file info gathering...")
    
    handler = MP3FileHandler()
    
    # Create a test file
    test_dir = Path(tempfile.mkdtemp(prefix='mp3_info_test_'))
    
    try:
        test_file = test_dir / 'test.mp3'
        test_content = b'ID3\x03\x00\x00\x00\x00\x00\x00' + b'X' * 1000  # 1KB+ file
        test_file.write_bytes(test_content)
        
        file_info = handler.get_file_info(test_file)
        
        expected_keys = {
            'path', 'filename', 'size_bytes', 'is_valid', 'duration_seconds',
            'bitrate', 'sample_rate', 'has_artwork', 'metadata', 'error'
        }
        
        if set(file_info.keys()) == expected_keys:
            print("✅ File info: Returns all expected keys")
        else:
            print(f"❌ File info: Expected keys {expected_keys}, got {set(file_info.keys())}")
            return False
        
        # Check basic properties
        if file_info['filename'] == 'test.mp3':
            print("✅ File info: Correct filename")
        else:
            print(f"❌ File info: Expected filename 'test.mp3', got '{file_info['filename']}'")
            return False
        
        if file_info['size_bytes'] > 1000:
            print("✅ File info: Correct file size")
        else:
            print(f"❌ File info: Expected size > 1000, got {file_info['size_bytes']}")
            return False
        
        return True
        
    finally:
        shutil.rmtree(test_dir)

def main():
    """Run all file handler tests"""
    print("🧪 Running MP3 File Handler Tests\n")
    print("=" * 60)
    
    tests = [
        ("MP3 File Detection", test_mp3_file_detection),
        ("Error Handling", test_error_handling),
        ("Metadata Extraction", test_metadata_extraction),
        ("Artwork Extraction", test_artwork_extraction),
        ("File Info Gathering", test_file_info)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 FILE HANDLER TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL FILE HANDLER TESTS PASSED!")
        print("✅ Phase 2.1 MP3 File Handling functionality is working")
        return True
    else:
        print("⚠️  Some file handler tests failed. Please review failures above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 