#!/usr/bin/env python3
"""
Phase 1 Regression Test Script
Verifies that all Phase 1 acceptance criteria have been met.
Run this test whenever making changes to ensure Phase 1 functionality remains intact.
"""

import os
import sys
import subprocess
from pathlib import Path

def test_project_structure():
    """Test that proper directory structure exists"""
    print("Testing project structure...")
    
    required_dirs = ['processors', 'templates', 'static', 'static/css', 'static/js', 'venv']
    required_files = ['requirements.txt', 'README.md', 'app.py', 'templates/index.html', 
                     'static/css/style.css', 'static/js/app.js']
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            print(f"❌ Missing directory: {directory}")
            return False
        print(f"✅ Directory exists: {directory}")
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Missing file: {file_path}")
            return False
        print(f"✅ File exists: {file_path}")
    
    return True

def test_dependencies():
    """Test that all dependencies can be imported"""
    print("\nTesting dependencies...")
    
    try:
        # Test imports in virtual environment
        result = subprocess.run([
            'venv/bin/python', '-c', 
            'import flask, mutagen, PIL, musicbrainzngs, requests; print("All imports successful")'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ All dependencies import successfully")
            return True
        else:
            print(f"❌ Import error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing dependencies: {e}")
        return False

def test_flask_app():
    """Test that Flask app can be created and basic routes work"""
    print("\nTesting Flask application...")
    
    try:
        # Test app creation
        result = subprocess.run([
            'venv/bin/python', '-c', 
            'from app import app; print("Flask app created successfully")'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Flask app imports and creates successfully")
            
            # Test app context and routes
            result = subprocess.run([
                'venv/bin/python', '-c', 
                '''
from app import app
with app.test_client() as client:
    response = client.get("/hello")
    assert response.status_code == 200
    assert b"Hello World" in response.data
    print("Basic route test passed")
                '''
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Basic route (/hello) works correctly")
                return True
            else:
                print(f"❌ Route test failed: {result.stderr}")
                return False
        else:
            print(f"❌ Flask app creation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing Flask app: {e}")
        return False

def test_html_template():
    """Test that HTML template renders correctly"""
    print("\nTesting HTML template...")
    
    try:
        result = subprocess.run([
            'venv/bin/python', '-c', 
            '''
from app import app
with app.test_client() as client:
    response = client.get("/")
    assert response.status_code == 200
    assert b"MP3 Artwork Manager" in response.data
    assert b"Traktor 3" in response.data
    print("Template renders successfully")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ HTML template renders correctly with expected content")
            return True
        else:
            print(f"❌ Template test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing template: {e}")
        return False

def test_requirements_content():
    """Test that requirements.txt contains expected dependencies"""
    print("\nTesting requirements.txt content...")
    
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        required_packages = ['Flask>=2.0.0', 'mutagen>=1.45.0', 'Pillow>=9.0.0', 
                           'musicbrainzngs>=0.7.0', 'requests>=2.25.0']
        
        for package in required_packages:
            if package not in content:
                print(f"❌ Missing package in requirements.txt: {package}")
                return False
            print(f"✅ Package found: {package}")
        
        return True
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        return False

def main():
    """Run all Phase 1 regression tests"""
    print("🧪 Running Phase 1 Regression Tests")
    print("These tests ensure Phase 1 functionality remains intact\n")
    print("=" * 60)
    
    tests = [
        ("Project Structure", test_project_structure),
        ("Requirements Content", test_requirements_content),
        ("Dependencies", test_dependencies), 
        ("Flask Application", test_flask_app),
        ("HTML Template", test_html_template)
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
    print(f"📊 PHASE 1 REGRESSION TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 1 FUNCTIONALITY IS INTACT!")
        print("✅ Safe to continue development")
        return True
    else:
        print("⚠️  Phase 1 regression detected! Please fix failures before continuing.")
        print("🔧 This indicates recent changes may have broken existing functionality.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 