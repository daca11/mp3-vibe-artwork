#!/usr/bin/env python3
"""
Phase 2 Unified Regression Test Script
Tests both Phase 2.1 (MP3 File Handling) and Phase 2.2 (Basic Image Processing) functionality.
"""

import sys
import subprocess

def test_phase2_imports():
    """Test that all Phase 2 imports work correctly"""
    print("Testing Phase 2 imports...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.file_handler import MP3FileHandler
from processors.artwork_processor import ArtworkProcessor

# Test instantiation
mp3_handler = MP3FileHandler()
artwork_processor = ArtworkProcessor()

print("All Phase 2 modules imported and instantiated successfully")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Phase 2 imports: All imports successful")
            return True
        else:
            print(f"❌ Phase 2 imports: Import failed - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 2 imports: Error testing imports - {e}")
        return False

def test_phase2_1_functionality():
    """Test Phase 2.1 MP3 File Handling functionality"""
    print("\nTesting Phase 2.1: MP3 File Handling...")
    
    try:
        # Run the file handler tests
        result = subprocess.run([
            'python', 'test_file_handler.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and "🎉 ALL FILE HANDLER TESTS PASSED!" in result.stdout:
            print("✅ Phase 2.1 MP3 File Handling: All tests passed")
            return True
        else:
            print("❌ Phase 2.1 MP3 File Handling: Tests failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 2.1 MP3 File Handling: Error running tests - {e}")
        return False

def test_phase2_2_functionality():
    """Test Phase 2.2 Basic Image Processing functionality"""
    print("\nTesting Phase 2.2: Basic Image Processing...")
    
    try:
        # Run the artwork processor tests
        result = subprocess.run([
            'python', 'test_artwork_processor.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and "🎉 ALL ARTWORK PROCESSOR TESTS PASSED!" in result.stdout:
            print("✅ Phase 2.2 Image Processing: All tests passed")
            return True
        else:
            print("❌ Phase 2.2 Image Processing: Tests failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 2.2 Image Processing: Error running tests - {e}")
        return False

def test_traktor_specifications():
    """Test that Traktor 3 specifications are correctly implemented across both modules"""
    print("\nTesting Traktor 3 specifications compliance...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.file_handler import MP3FileHandler
from processors.artwork_processor import ArtworkProcessor

mp3_handler = MP3FileHandler()
artwork_processor = ArtworkProcessor()

# Verify MP3 file extensions
expected_extensions = {".mp3", ".MP3", ".Mp3", ".mP3"}
assert mp3_handler.MP3_EXTENSIONS == expected_extensions, f"MP3 extensions mismatch"

# Verify artwork specifications
assert artwork_processor.MAX_WIDTH == 500, f"Expected MAX_WIDTH=500, got {artwork_processor.MAX_WIDTH}"
assert artwork_processor.MAX_HEIGHT == 500, f"Expected MAX_HEIGHT=500, got {artwork_processor.MAX_HEIGHT}"
assert artwork_processor.MAX_FILE_SIZE == 500 * 1024, f"Expected MAX_FILE_SIZE=512000, got {artwork_processor.MAX_FILE_SIZE}"
assert artwork_processor.SUPPORTED_FORMATS == {"JPEG", "PNG"}, f"Expected formats JPEG/PNG, got {artwork_processor.SUPPORTED_FORMATS}"

print("All Traktor 3 specifications correctly implemented across Phase 2 modules")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Traktor specifications: All specifications correctly implemented")
            return True
        else:
            print(f"❌ Traktor specifications: Specification error - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Traktor specifications: Error testing specifications - {e}")
        return False

def test_integration_readiness():
    """Test that Phase 2.1 and 2.2 modules can work together"""
    print("\nTesting Phase 2 integration readiness...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.file_handler import MP3FileHandler
from processors.artwork_processor import ArtworkProcessor
import io
from PIL import Image

# Create test instances
mp3_handler = MP3FileHandler()
artwork_processor = ArtworkProcessor()

# Test that they can be used together
print("MP3FileHandler methods available:", [method for method in dir(mp3_handler) if not method.startswith("_")])
print("ArtworkProcessor methods available:", [method for method in dir(artwork_processor) if not method.startswith("_")])

# Test compatibility - artwork processor can handle data that would come from MP3 handler
# Create a test image
test_img = Image.new("RGB", (300, 200), "red")
buffer = io.BytesIO()
test_img.save(buffer, format="JPEG", quality=95)
test_image_data = buffer.getvalue()

# Test artwork validation
is_valid, issues = artwork_processor.validate_artwork(test_image_data)
print(f"Artwork validation test: valid={is_valid}, issues={len(issues)}")

# Test image info extraction
image_info = artwork_processor.get_image_info(test_image_data)
print(f"Image info extraction: format={image_info.get('format')}, size={image_info.get('width')}x{image_info.get('height')}")

print("Phase 2.1 and 2.2 modules are ready for integration")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Integration readiness: Modules are compatible and ready for integration")
            return True
        else:
            print(f"❌ Integration readiness: Compatibility issues - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Integration readiness: Error testing integration - {e}")
        return False

def main():
    """Run all Phase 2 unified regression tests"""
    print("🧪 Running Phase 2 Unified Regression Tests")
    print("Testing MP3 File Handling + Basic Image Processing\n")
    print("=" * 70)
    
    tests = [
        ("Phase 2 Imports", test_phase2_imports),
        ("Traktor Specifications", test_traktor_specifications),
        ("Phase 2.1: MP3 File Handling", test_phase2_1_functionality),
        ("Phase 2.2: Image Processing", test_phase2_2_functionality),
        ("Integration Readiness", test_integration_readiness)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 50)
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 70)
    print(f"📊 PHASE 2 UNIFIED TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 2 FUNCTIONALITY IS INTACT!")
        print("✅ MP3 file handling works correctly")
        print("✅ Image processing works correctly") 
        print("✅ Modules are ready for Phase 3 integration")
        return True
    else:
        print("⚠️  Phase 2 regression detected! Please fix failures before continuing.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 