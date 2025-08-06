#!/usr/bin/env python3
"""
Phase 2.2 Regression Test Script
Tests image processing functionality to ensure it remains intact.
"""

import sys
import subprocess

def test_phase2_2_imports():
    """Test that all Phase 2.2 imports work correctly"""
    print("Testing Phase 2.2 imports...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.artwork_processor import ArtworkProcessor
processor = ArtworkProcessor()
print("ArtworkProcessor imported and instantiated successfully")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Phase 2.2 imports: All imports successful")
            return True
        else:
            print(f"❌ Phase 2.2 imports: Import failed - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 2.2 imports: Error testing imports - {e}")
        return False

def test_phase2_2_functionality():
    """Test that Phase 2.2 image processing works correctly"""
    print("\nTesting Phase 2.2 Image Processing...")
    
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
    """Test that Traktor 3 specifications are correctly implemented"""
    print("\nTesting Traktor 3 specifications...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.artwork_processor import ArtworkProcessor
processor = ArtworkProcessor()

# Verify Traktor specifications are correct
assert processor.MAX_WIDTH == 500, f"Expected MAX_WIDTH=500, got {processor.MAX_WIDTH}"
assert processor.MAX_HEIGHT == 500, f"Expected MAX_HEIGHT=500, got {processor.MAX_HEIGHT}"
assert processor.MAX_FILE_SIZE == 500 * 1024, f"Expected MAX_FILE_SIZE=512000, got {processor.MAX_FILE_SIZE}"
assert processor.SUPPORTED_FORMATS == {"JPEG", "PNG"}, f"Expected formats JPEG/PNG, got {processor.SUPPORTED_FORMATS}"

print("All Traktor 3 specifications correctly implemented")
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

def main():
    """Run all Phase 2.2 regression tests"""
    print("🧪 Running Phase 2.2 Regression Tests")
    print("Testing Basic Image Processing functionality\n")
    print("=" * 60)
    
    tests = [
        ("Phase 2.2 Imports", test_phase2_2_imports),
        ("Traktor Specifications", test_traktor_specifications),
        ("Phase 2.2 Functionality", test_phase2_2_functionality)
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
    print(f"📊 PHASE 2.2 REGRESSION TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 2.2 FUNCTIONALITY IS INTACT!")
        print("✅ Image processing works correctly")
        return True
    else:
        print("⚠️  Phase 2.2 regression detected! Please fix failures before continuing.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 