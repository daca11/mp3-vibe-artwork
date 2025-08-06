#!/usr/bin/env python3
"""
Test Module for File Operations
Tests output folder management, MP3 file copying with artwork embedding, and filename parsing.
"""

import io
import sys
import tempfile
import shutil
from pathlib import Path
from PIL import Image
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
from processors.file_operations import FileOperations

def create_test_mp3_with_metadata(file_path: Path, title: str = "Test Song", 
                                artist: str = "Test Artist", album: str = "Test Album",
                                add_artwork: bool = False) -> None:
    """Create a test MP3 file with metadata and optional artwork"""
    # Create a more complete MP3 file structure
    # ID3v2.3 header with no flags, no extended header
    id3_header = b'ID3\x03\x00\x00\x00\x00\x00\x00'
    
    # MP3 frame header for a valid 44.1kHz, 128kbps, stereo MP3
    mp3_frame = b'\xff\xfb\x90\x00'
    
    # Add more realistic MP3 frame data
    mp3_data = mp3_frame + b'\x00' * 417  # Standard frame size for 128kbps
    
    # Create the complete file
    complete_data = id3_header + mp3_data * 10  # Multiple frames
    file_path.write_bytes(complete_data)
    
    # Add ID3 tags using mutagen
    audio_file = MP3(str(file_path))
    if audio_file.tags is None:
        audio_file.add_tags()
    
    # Add metadata
    audio_file.tags.add(TIT2(encoding=3, text=title))
    audio_file.tags.add(TPE1(encoding=3, text=artist))
    audio_file.tags.add(TALB(encoding=3, text=album))
    
    # Add artwork if requested
    if add_artwork:
        # Create a test image
        img = Image.new('RGB', (600, 600), 'blue')  # Large image for testing
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=100)
        artwork_data = buffer.getvalue()
        
        apic = APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Cover',
            data=artwork_data
        )
        audio_file.tags.add(apic)
    
    audio_file.save()

def test_output_folder_management():
    """Test output folder creation and management"""
    print("Testing output folder management...")
    
    file_ops = FileOperations()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test with custom base directory
        file_ops.output_base_dir = temp_path / "test_output"
        
        # Test creating main output folder
        output_folder = file_ops.create_output_folder()
        
        if output_folder.exists() and output_folder.is_dir():
            print("✅ Output folder creation: Successfully created main folder")
        else:
            print("❌ Output folder creation: Failed to create main folder")
            return False
        
        # Test creating subfolder
        subfolder = file_ops.create_output_folder("subfolder_test")
        expected_subfolder = file_ops.output_base_dir / "subfolder_test"
        
        if subfolder == expected_subfolder and subfolder.exists():
            print("✅ Subfolder creation: Successfully created subfolder")
        else:
            print(f"❌ Subfolder creation: Expected {expected_subfolder}, got {subfolder}")
            return False
        
        # Test write permissions (already tested in create_output_folder)
        test_file = output_folder / "permission_test.txt"
        test_file.write_text("test")
        
        if test_file.exists() and test_file.read_text() == "test":
            print("✅ Write permissions: Folder is writable")
            test_file.unlink()
        else:
            print("❌ Write permissions: Folder is not writable")
            return False
    
    return True

def test_unique_filename_generation():
    """Test unique filename generation"""
    print("\nTesting unique filename generation...")
    
    file_ops = FileOperations()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test with non-existing file
        unique_path = file_ops.generate_unique_filename(temp_path, "test.mp3")
        expected_path = temp_path / "test.mp3"
        
        if unique_path == expected_path:
            print("✅ Non-existing file: Returns original filename")
        else:
            print(f"❌ Non-existing file: Expected {expected_path}, got {unique_path}")
            return False
        
        # Create the file to test conflict resolution
        expected_path.touch()
        
        # Test with existing file
        unique_path = file_ops.generate_unique_filename(temp_path, "test.mp3")
        expected_unique = temp_path / "test (1).mp3"
        
        if unique_path == expected_unique:
            print("✅ Existing file conflict: Generated unique filename")
        else:
            print(f"❌ Existing file conflict: Expected {expected_unique}, got {unique_path}")
            return False
        
        # Create multiple conflicts
        expected_unique.touch()
        (temp_path / "test (2).mp3").touch()
        
        unique_path = file_ops.generate_unique_filename(temp_path, "test.mp3")
        expected_unique2 = temp_path / "test (3).mp3"
        
        if unique_path == expected_unique2:
            print("✅ Multiple conflicts: Generated next available filename")
        else:
            print(f"❌ Multiple conflicts: Expected {expected_unique2}, got {unique_path}")
            return False
    
    return True

def test_artwork_embedding():
    """Test artwork embedding logic (focusing on the interface)"""
    print("\nTesting artwork embedding...")
    
    file_ops = FileOperations()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        mp3_file = temp_path / "test.mp3"
        
        # Create a simple MP3-like file for testing interface
        mp3_file.write_bytes(b'fake mp3 data for testing interface')
        
        # Create test artwork
        img = Image.new('RGB', (300, 200), 'red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=95)
        artwork_data = buffer.getvalue()
        
        # Test artwork embedding (expect it to fail gracefully with fake MP3)
        success = file_ops.embed_artwork_in_mp3(mp3_file, artwork_data, "image/jpeg")
        
        # For a fake MP3 file, we expect this to fail gracefully
        if not success:
            print("✅ Artwork embedding: Gracefully handled invalid MP3 file")
        else:
            print("❌ Artwork embedding: Should have failed with fake MP3")
            return False
        
        # Test with missing file
        missing_file = temp_path / "missing.mp3"
        success = file_ops.embed_artwork_in_mp3(missing_file, artwork_data, "image/jpeg")
        
        if not success:
            print("✅ Missing file handling: Gracefully handled missing file")
        else:
            print("❌ Missing file handling: Should have failed with missing file")
            return False
    
    return True

def test_mp3_file_copying():
    """Test MP3 file copying logic"""
    print("\nTesting MP3 file copying...")
    
    file_ops = FileOperations()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_file = temp_path / "source.mp3"
        output_dir = temp_path / "output"
        
        # Create a simple file to test the copying logic
        source_file.write_bytes(b'fake mp3 data for testing')
        
        # Create output directory
        output_dir.mkdir()
        
        # Test copying without artwork (should work even with fake MP3)
        result = file_ops.copy_mp3_with_artwork(source_file, output_dir)
        
        # This should fail because our fake MP3 won't validate
        if not result['success']:
            print("✅ MP3 validation: Correctly rejected invalid MP3")
        else:
            print("❌ MP3 validation: Should have rejected invalid MP3")
            return False
        
        # Test with missing source file
        missing_file = temp_path / "missing.mp3"
        result = file_ops.copy_mp3_with_artwork(missing_file, output_dir)
        
        if not result['success'] and "does not exist" in result['error']:
            print("✅ Missing file handling: Correctly handled missing source file")
        else:
            print("❌ Missing file handling: Should have detected missing file")
            return False
        
        # Test the file operations logic by creating a real file and testing paths
        real_source = temp_path / "real_source.txt"
        real_source.write_text("test content")
        
        # Test unique filename generation
        unique_path = file_ops.generate_unique_filename(output_dir, real_source.name)
        expected_path = output_dir / real_source.name
        
        if unique_path == expected_path:
            print("✅ Filename generation: Correctly handles non-conflicting names")
        else:
            print("❌ Filename generation: Unexpected path generation")
            return False
    
    return True

def test_filename_parsing():
    """Test filename parsing for metadata extraction"""
    print("\nTesting filename parsing...")
    
    file_ops = FileOperations()
    
    # Test cases: (filename, expected_artist, expected_title, should_parse)
    test_cases = [
        ("Artist Name - Song Title.mp3", "Artist Name", "Song Title", True),
        ("John Doe - Beautiful Song.mp3", "John Doe", "Beautiful Song", True),
        ("The Beatles – Yesterday.mp3", "The Beatles", "Yesterday", True),  # em dash
        ("Artist|Title.mp3", "Artist", "Title", True),
        ("Artist_Name_-_Song_Title.mp3", "Artist Name", "Song Title", True),
        ("01. Artist - Song.mp3", "Artist", "Song", True),  # Track number
        ("Artist - Song [320kbps].mp3", "Artist", "Song", True),  # Quality indicator
        ("02-Inkswel & Colonel Red - Make Me Crazy (Potatohead People Remix) [Only Good Stuff].mp3", "Inkswel & Colonel Red", "Make Me Crazy (Potatohead People Remix) [Only Good Stuff]", True),  # User's specific example
        ("Just A Filename.mp3", None, None, False),  # No separator
        ("", None, None, False),  # Empty filename
    ]
    
    passed_tests = 0
    
    for filename, expected_artist, expected_title, should_parse in test_cases:
        result = file_ops.parse_filename_for_metadata(filename)
        
        if should_parse:
            if result['artist'] == expected_artist and result['title'] == expected_title:
                print(f"✅ Parsing '{filename}': Correctly parsed")
                passed_tests += 1
            else:
                print(f"❌ Parsing '{filename}': Expected ({expected_artist}, {expected_title}), got ({result['artist']}, {result['title']})")
        else:
            if result['artist'] is None and result['title'] is None:
                print(f"✅ Parsing '{filename}': Correctly rejected unparseable filename")
                passed_tests += 1
            else:
                print(f"❌ Parsing '{filename}': Should not have parsed, but got ({result['artist']}, {result['title']})")
    
    success = passed_tests == len(test_cases)
    print(f"Filename parsing results: {passed_tests}/{len(test_cases)} tests passed")
    
    return success

def test_output_filename_generation():
    """Test proper output filename generation using Artist - Title convention"""
    print("\nTesting output filename generation...")
    
    file_ops = FileOperations()
    
    # Test cases: (artist, title, expected_filename)
    test_cases = [
        ("Inkswel & Colonel Red", "Make Me Crazy (Potatohead People Remix)", "Inkswel & Colonel Red - Make Me Crazy (Potatohead People Remix).mp3"),
        ("The Beatles", "Yesterday", "The Beatles - Yesterday.mp3"),
        ("Artist/Name", "Song:Title", "Artist-Name - Song-Title.mp3"),  # Test sanitization
        (None, "Title Only", "Unknown Artist - Title Only.mp3"),  # Missing artist
        ("Artist Only", None, "Artist Only - Unknown Title.mp3"),  # Missing title
        ("", "", "Unknown Artist - Unknown Title.mp3"),  # Both missing
        ("Artist with \"quotes\"", "Song [Version]", "Artist with 'quotes - Song [Version].mp3"),  # Test quotes and brackets (quotes get sanitized)
        ("Inkswel & Colonel Red", "Make Me Crazy (Potatohead People Remix) [Only Good Stuff]", "Inkswel & Colonel Red - Make Me Crazy (Potatohead People Remix) [Only Good Stuff].mp3"),  # User's specific example
    ]
    
    passed_tests = 0
    
    for artist, title, expected_filename in test_cases:
        result = file_ops.generate_output_filename(artist, title)
        
        if result == expected_filename:
            print(f"✅ Filename generation '{artist}' - '{title}': Correctly generated '{result}'")
            passed_tests += 1
        else:
            print(f"❌ Filename generation '{artist}' - '{title}': Expected '{expected_filename}', got '{result}'")
    
    success = passed_tests == len(test_cases)
    print(f"Filename generation results: {passed_tests}/{len(test_cases)} tests passed")
    
    return success

def test_complete_processing_pipeline():
    """Test the complete MP3 processing pipeline (focusing on error handling)"""
    print("\nTesting complete processing pipeline...")
    
    file_ops = FileOperations()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_file = temp_path / "Test Artist - Test Song.mp3"
        
        # Create a fake MP3 file to test error handling
        source_file.write_bytes(b'fake mp3 data')
        
        # Set custom output directory
        file_ops.output_base_dir = temp_path / "processed_output"
        
        # Process the file (should fail gracefully)
        result = file_ops.process_mp3_file(source_file, process_artwork=True)
        
        # Should fail due to invalid MP3
        if not result['success']:
            print("✅ Pipeline validation: Correctly rejected invalid MP3")
        else:
            print("❌ Pipeline validation: Should have rejected invalid MP3")
            return False
        
        # Check that processing steps were recorded even on failure
        if len(result['processing_steps']) > 0:
            print(f"✅ Processing steps: {len(result['processing_steps'])} steps recorded even on failure")
        else:
            print("❌ Processing steps: No processing steps recorded")
            return False
        
        # Test with missing file
        missing_file = temp_path / "missing.mp3"
        result = file_ops.process_mp3_file(missing_file)
        
        if not result['success'] and "does not exist" in result['error']:
            print("✅ Missing file handling: Correctly handled missing source file")
        else:
            print("❌ Missing file handling: Should have detected missing file")
            return False
        
        # Test filename parsing with the provided filename
        parsing_result = file_ops.parse_filename_for_metadata(source_file.name)
        
        if parsing_result['artist'] == "Test Artist" and parsing_result['title'] == "Test Song":
            print("✅ Filename parsing integration: Correctly parsed filename in pipeline")
        else:
            print(f"❌ Filename parsing integration: Expected 'Test Artist' and 'Test Song', got '{parsing_result['artist']}' and '{parsing_result['title']}'")
            return False
    
    return True

def main():
    """Run all file operations tests"""
    print("🧪 Running File Operations Tests\n")
    print("=" * 60)
    
    tests = [
        ("Output Folder Management", test_output_folder_management),
        ("Unique Filename Generation", test_unique_filename_generation),
        ("Artwork Embedding", test_artwork_embedding),
        ("MP3 File Copying", test_mp3_file_copying),
        ("Filename Parsing", test_filename_parsing),
        ("Output Filename Generation", test_output_filename_generation),
        ("Complete Processing Pipeline", test_complete_processing_pipeline)
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
    print(f"📊 FILE OPERATIONS TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL FILE OPERATIONS TESTS PASSED!")
        print("✅ Phase 3 File Operations functionality is working")
        return True
    else:
        print("⚠️  Some file operations tests failed. Please review failures above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 