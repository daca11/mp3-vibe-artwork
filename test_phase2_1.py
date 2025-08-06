#!/usr/bin/env python3
"""
Phase 2.1 Regression Test Script
Tests MP3 file handling functionality to ensure it remains intact.
"""

import sys
import subprocess

def test_phase2_1_functionality():
    """Test that Phase 2.1 MP3 file handling works correctly"""
    print("Testing Phase 2.1 MP3 File Handling...")
    
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

def test_imports():
    """Test that all Phase 2.1 imports work correctly"""
    print("\nTesting Phase 2.1 imports...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from processors.file_handler import MP3FileHandler
handler = MP3FileHandler()
print("MP3FileHandler imported and instantiated successfully")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Phase 2.1 imports: All imports successful")
            return True
        else:
            print(f"❌ Phase 2.1 imports: Import failed - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 2.1 imports: Error testing imports - {e}")
        return False

def main():
    """Run all Phase 2.1 regression tests"""
    print("🧪 Running Phase 2.1 Regression Tests")
    print("Testing MP3 File Handling functionality\n")
    print("=" * 50)
    
    tests = [
        ("Phase 2.1 Imports", test_imports),
        ("Phase 2.1 Functionality", test_phase2_1_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 PHASE 2.1 REGRESSION TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 2.1 FUNCTIONALITY IS INTACT!")
        print("✅ MP3 file handling works correctly")
        return True
    else:
        print("⚠️  Phase 2.1 regression detected! Please fix failures before continuing.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 