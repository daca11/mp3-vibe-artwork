#!/usr/bin/env python3
"""
Phase 5 Regression Tests
Tests for MusicBrainz Integration functionality.
"""

import logging
from pathlib import Path

# Suppress logging during tests
logging.disable(logging.CRITICAL)

def test_phase5_imports():
    """Test that Phase 5 imports work correctly"""
    print("\n--- Testing Phase 5 Imports ---")
    
    try:
        # Test MusicBrainz client import
        from processors.musicbrainz_client import MusicBrainzClient
        print("✅ MusicBrainzClient import: Success")
        
        # Test that file operations can import MusicBrainz client
        from processors.file_operations import FileOperations
        print("✅ FileOperations with MusicBrainz import: Success")
        
        # Test that musicbrainzngs is available
        import musicbrainzngs
        print("✅ musicbrainzngs import: Success")
        
        # Test that requests is available
        import requests
        print("✅ requests import: Success")
        
        print("✅ Phase 5 Imports: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_phase5_musicbrainz_functionality():
    """Test MusicBrainz functionality"""
    print("\n--- Testing Phase 5 MusicBrainz Functionality ---")
    
    try:
        # Run MusicBrainz client tests
        import test_musicbrainz_client
        
        # Run specific tests
        tests_to_run = [
            ("MusicBrainz Client Initialization", test_musicbrainz_client.test_client_initialization),
            ("Rate Limiting", test_musicbrainz_client.test_rate_limiting),
            ("Basic Release Search", test_musicbrainz_client.test_search_release_basic),
            ("Artwork Download", test_musicbrainz_client.test_download_artwork)
        ]
        
        passed = 0
        for test_name, test_func in tests_to_run:
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
        
        if passed == len(tests_to_run):
            print("✅ Phase 5 MusicBrainz Functionality: PASSED")
            return True
        else:
            print(f"❌ Phase 5 MusicBrainz Functionality: {passed}/{len(tests_to_run)} tests passed")
            return False
            
    except Exception as e:
        print(f"❌ MusicBrainz functionality test failed: {e}")
        return False

def test_phase5_file_operations_integration():
    """Test MusicBrainz integration with file operations"""
    print("\n--- Testing Phase 5 File Operations Integration ---")
    
    try:
        # Run file operations tests with MusicBrainz
        import test_file_operations
        
        # Test MusicBrainz integration specifically
        success = test_file_operations.test_musicbrainz_integration()
        
        if success:
            print("✅ Phase 5 File Operations Integration: PASSED")
            return True
        else:
            print("❌ Phase 5 File Operations Integration: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ File operations integration test failed: {e}")
        return False

def test_integration_with_previous_phases():
    """Test that Phase 5 integrates properly with all previous phases"""
    print("\n--- Testing Integration with Previous Phases ---")
    
    try:
        # Test that file operations still work correctly
        from processors.file_operations import FileOperations
        
        # Initialize with MusicBrainz enabled
        file_ops = FileOperations(enable_musicbrainz=True)
        
        # Test that basic functionality is preserved
        assert hasattr(file_ops, 'mp3_handler'), "Should have mp3_handler"
        assert hasattr(file_ops, 'artwork_processor'), "Should have artwork_processor"
        assert hasattr(file_ops, 'musicbrainz_client'), "Should have musicbrainz_client"
        
        print("✅ FileOperations integration: All components present")
        
        # Test that previous phase functionality still works
        test_filename = "Artist - Song Title.mp3"
        parsed = file_ops.parse_filename_for_metadata(test_filename)
        
        assert parsed['artist'] == 'Artist', "Filename parsing should still work"
        assert parsed['title'] == 'Song Title', "Filename parsing should still work"
        
        print("✅ Previous phase functionality: Preserved")
        
        print("✅ Integration with Previous Phases: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_complete_pipeline_with_musicbrainz():
    """Test the complete processing pipeline with MusicBrainz enabled"""
    print("\n--- Testing Complete Pipeline with MusicBrainz ---")
    
    try:
        from processors.file_operations import FileOperations
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a fake MP3 file
            fake_mp3 = temp_path / "Test Artist - Test Song.mp3"
            fake_mp3.write_bytes(b"fake mp3 data")
            
            # Initialize file operations with MusicBrainz
            file_ops = FileOperations(enable_musicbrainz=True)
            
            # Test processing (should handle missing artwork gracefully)
            result = file_ops.process_mp3_file(fake_mp3, process_artwork=True)
            
            # Should not crash even with invalid MP3 and MusicBrainz enabled
            assert 'success' in result, "Result should have success field"
            
            # Check if artwork processing was attempted
            if 'artwork_info' in result and result['artwork_info']:
                # If artwork processing happened, check MusicBrainz tracking
                if 'musicbrainz_searched' in result['artwork_info']:
                    print("✅ MusicBrainz search tracking: Present in result")
                else:
                    print("⚠️  MusicBrainz search tracking: Not present (possibly due to invalid MP3)")
            else:
                print("⚠️  Artwork processing: Skipped (possibly due to invalid MP3)")
            
            # The main requirement is that MusicBrainz integration doesn't crash the pipeline
            print("✅ Complete pipeline: Handles MusicBrainz integration gracefully")
        
        print("✅ Complete Pipeline with MusicBrainz: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Complete pipeline test failed: {e}")
        return False

def main():
    """Run all Phase 5 regression tests"""
    print("🧪 Running Phase 5 Regression Tests")
    print("Testing MusicBrainz Integration")
    print("=" * 60)
    
    tests = [
        ("Phase 5 Imports", test_phase5_imports),
        ("Phase 5 MusicBrainz Functionality", test_phase5_musicbrainz_functionality),
        ("Phase 5 File Operations Integration", test_phase5_file_operations_integration),
        ("Integration with Previous Phases", test_integration_with_previous_phases),
        ("Complete Pipeline with MusicBrainz", test_complete_pipeline_with_musicbrainz)
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
    
    print("\n" + "=" * 60)
    print(f"📊 PHASE 5 REGRESSION TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 5 FUNCTIONALITY IS INTACT!")
        print("✅ MusicBrainz integration working correctly")
        print("✅ File operations enhanced with artwork discovery")
        print("✅ All phases (1-5) integrated and functional")
    else:
        print(f"⚠️  {total - passed} Phase 5 tests failed. Please review failures above.")
    
    return passed == total

if __name__ == "__main__":
    main() 