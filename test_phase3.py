#!/usr/bin/env python3
"""
Phase 3 Regression Test Script
Tests file operations functionality to ensure it remains intact.
"""

import sys
import subprocess

def test_phase3_imports():
    """Test that all Phase 3 imports work correctly"""
    print("Testing Phase 3 imports...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.file_operations import FileOperations
from processors.file_handler import MP3FileHandler
from processors.artwork_processor import ArtworkProcessor

# Test instantiation
file_ops = FileOperations()
mp3_handler = MP3FileHandler()
artwork_processor = ArtworkProcessor()

print("All Phase 3 modules imported and instantiated successfully")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Phase 3 imports: All imports successful")
            return True
        else:
            print(f"❌ Phase 3 imports: Import failed - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 3 imports: Error testing imports - {e}")
        return False

def test_phase3_functionality():
    """Test that Phase 3 file operations work correctly"""
    print("\nTesting Phase 3 File Operations...")
    
    try:
        # Run the file operations tests
        result = subprocess.run([
            'python', 'test_file_operations.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and "🎉 ALL FILE OPERATIONS TESTS PASSED!" in result.stdout:
            print("✅ Phase 3 File Operations: All tests passed")
            return True
        else:
            print("❌ Phase 3 File Operations: Tests failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 3 File Operations: Error running tests - {e}")
        return False

def test_integration_with_previous_phases():
    """Test that Phase 3 integrates correctly with Phases 1 and 2"""
    print("\nTesting Phase 3 integration with previous phases...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.file_operations import FileOperations
from pathlib import Path
import tempfile

# Create a file operations instance
file_ops = FileOperations()

# Test that it can use MP3FileHandler and ArtworkProcessor
mp3_handler = file_ops.mp3_handler
artwork_processor = file_ops.artwork_processor

print(f"FileOperations has mp3_handler: {mp3_handler.__class__.__name__}")
print(f"FileOperations has artwork_processor: {artwork_processor.__class__.__name__}")

# Test filename parsing (Phase 3 feature)
parsing_result = file_ops.parse_filename_for_metadata("Artist - Song.mp3")
print(f"Filename parsing: Artist='{parsing_result['artist']}', Title='{parsing_result['title']}'")

# Test output folder creation (Phase 3 feature)
with tempfile.TemporaryDirectory() as temp_dir:
    file_ops.output_base_dir = Path(temp_dir) / "test_output"
    output_dir = file_ops.create_output_folder()
    print(f"Output folder created: {output_dir.exists()}")

print("Phase 3 integration with Phases 1 and 2 successful")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Phase integration: Successfully integrates with previous phases")
            return True
        else:
            print(f"❌ Phase integration: Integration failed - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase integration: Error testing integration - {e}")
        return False

def test_complete_workflow_simulation():
    """Test a simulated complete workflow using all phases"""
    print("\nTesting complete workflow simulation...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.file_operations import FileOperations
from processors.file_handler import MP3FileHandler
from processors.artwork_processor import ArtworkProcessor
from pathlib import Path
import tempfile
from PIL import Image
import io

# Simulate complete workflow
print("Step 1: Initialize all processors")
file_ops = FileOperations()
mp3_handler = MP3FileHandler()
artwork_processor = ArtworkProcessor()

print("Step 2: Test filename parsing")
filename = "The Beatles - Yesterday.mp3"
parsing_result = file_ops.parse_filename_for_metadata(filename)
print(f"Parsed: {parsing_result['artist']} - {parsing_result['title']}")

print("Step 3: Test image processing capabilities")
# Create test image
img = Image.new('RGB', (800, 600), 'blue')  # Oversized image
buffer = io.BytesIO()
img.save(buffer, format='JPEG', quality=100)
test_artwork = buffer.getvalue()

# Validate and process artwork
is_valid, issues = artwork_processor.validate_artwork(test_artwork)
print(f"Artwork validation: valid={is_valid}, issues={len(issues)}")

if not is_valid:
    processed_result = artwork_processor.process_artwork(test_artwork, force_compliance=True)
    print(f"Artwork processing: compliant={processed_result['is_compliant']}")

print("Step 4: Test output folder management")
with tempfile.TemporaryDirectory() as temp_dir:
    file_ops.output_base_dir = Path(temp_dir) / "workflow_output"
    output_dir = file_ops.create_output_folder("session_001")
    print(f"Output directory created: {output_dir}")
    
    # Test unique filename generation
    unique_path = file_ops.generate_unique_filename(output_dir, "test.mp3")
    print(f"Unique filename: {unique_path.name}")

print("Complete workflow simulation successful - all phases working together")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Workflow simulation: Complete workflow simulation successful")
            return True
        else:
            print(f"❌ Workflow simulation: Simulation failed - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Workflow simulation: Error in simulation - {e}")
        return False

def main():
    """Run all Phase 3 regression tests"""
    print("🧪 Running Phase 3 Regression Tests")
    print("Testing File Operations functionality\n")
    print("=" * 60)
    
    tests = [
        ("Phase 3 Imports", test_phase3_imports),
        ("Phase 3 Functionality", test_phase3_functionality),
        ("Integration with Previous Phases", test_integration_with_previous_phases),
        ("Complete Workflow Simulation", test_complete_workflow_simulation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 60)
    print(f"📊 PHASE 3 REGRESSION TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 3 FUNCTIONALITY IS INTACT!")
        print("✅ File operations work correctly")
        print("✅ Integration with Phases 1 & 2 successful")
        print("✅ Complete workflow pipeline ready")
        return True
    else:
        print("⚠️  Phase 3 regression detected! Please fix failures before continuing.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 