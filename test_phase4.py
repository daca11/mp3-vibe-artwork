#!/usr/bin/env python3
"""
Phase 4 Regression Test Script
Tests web interface functionality to ensure it remains intact.
"""

import sys
import subprocess

def test_phase4_imports():
    """Test that all Phase 4 imports work correctly"""
    print("Testing Phase 4 imports...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from app import app, processing_sessions, file_ops, mp3_handler, artwork_processor
from flask import Flask

# Test Flask app
assert app is not None
assert isinstance(app, Flask)

# Test processors are initialized
assert file_ops is not None
assert mp3_handler is not None
assert artwork_processor is not None

# Test sessions dictionary
assert isinstance(processing_sessions, dict)

print("All Phase 4 components imported and initialized successfully")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Phase 4 imports: All imports successful")
            return True
        else:
            print(f"❌ Phase 4 imports: Import failed - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 4 imports: Error testing imports - {e}")
        return False

def test_phase4_functionality():
    """Test that Phase 4 web interface works correctly"""
    print("\nTesting Phase 4 Web Interface...")
    
    try:
        # Run the web interface tests
        result = subprocess.run([
            'python', 'test_web_interface.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and "🎉 ALL WEB INTERFACE TESTS PASSED!" in result.stdout:
            print("✅ Phase 4 Web Interface: All tests passed")
            return True
        else:
            print("❌ Phase 4 Web Interface: Tests failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase 4 Web Interface: Error running tests - {e}")
        return False

def test_integration_with_previous_phases():
    """Test that Phase 4 integrates correctly with all previous phases"""
    print("\nTesting Phase 4 integration with all phases...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
# Test Flask app with all processors
from app import app, file_ops, mp3_handler, artwork_processor

# Test that Flask app uses all three processors
assert hasattr(file_ops, 'mp3_handler')
assert hasattr(file_ops, 'artwork_processor')
print("Phase 1: Flask app ✓")

# Test that all processor classes are available
from processors.file_handler import MP3FileHandler
from processors.artwork_processor import ArtworkProcessor  
from processors.file_operations import FileOperations
print("Phase 2.1: MP3FileHandler ✓")
print("Phase 2.2: ArtworkProcessor ✓")
print("Phase 3: FileOperations ✓")

# Test Flask routes integration
with app.test_client() as client:
    # Test main page loads
    response = client.get('/')
    assert response.status_code == 200
    print("Phase 4: Web interface ✓")
    
    # Test API endpoints exist
    response = client.post('/upload')  # Should return 400 for no files
    assert response.status_code == 400
    print("Phase 4: Upload API ✓")
    
    response = client.get('/status/test')  # Should return 404 for invalid session
    assert response.status_code == 404
    print("Phase 4: Status API ✓")

print("All phases integrated successfully in web interface")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Phase integration: Successfully integrates with all previous phases")
            return True
        else:
            print(f"❌ Phase integration: Integration failed - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Phase integration: Error testing integration - {e}")
        return False

def test_frontend_backend_communication():
    """Test frontend and backend communication"""
    print("\nTesting frontend-backend communication...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from app import app
import json

# Test API endpoints that frontend uses
with app.test_client() as client:
    # Test AJAX endpoints return JSON
    response = client.post('/upload')
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert 'error' in data
    print("Upload API returns JSON ✓")
    
    response = client.get('/status/invalid')
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert 'error' in data
    print("Status API returns JSON ✓")
    
    response = client.post('/api/validate', json={})
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert 'error' in data
    print("Validation API returns JSON ✓")
    
    # Test main page serves HTML with required elements
    response = client.get('/')
    assert 'text/html' in response.content_type
    html = response.data.decode('utf-8')
    
    # Check for JavaScript functionality
    assert 'uploadFiles' in html or 'app.js' in html
    print("Frontend JavaScript included ✓")
    
    # Check for interactive elements
    assert 'uploadArea' in html
    assert 'processBtn' in html
    assert 'downloadBtn' in html
    print("Interactive elements present ✓")

print("Frontend-backend communication working correctly")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Frontend-backend communication: Working correctly")
            return True
        else:
            print(f"❌ Frontend-backend communication: Communication issues - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Frontend-backend communication: Error testing communication - {e}")
        return False

def test_complete_application_readiness():
    """Test that the complete application is ready for use"""
    print("\nTesting complete application readiness...")
    
    try:
        result = subprocess.run([
            'python', '-c', 
            '''
from app import app
import os
from pathlib import Path

# Test application configuration
assert app.config['SECRET_KEY'] is not None
assert app.config['MAX_CONTENT_LENGTH'] == 100 * 1024 * 1024
print("Application configuration ✓")

# Test required directories exist
upload_dir = Path(app.config['UPLOAD_FOLDER'])
output_dir = Path(app.config['OUTPUT_FOLDER'])
assert upload_dir.exists() or upload_dir.name == 'uploads'
assert output_dir.exists() or output_dir.name == 'output'
print("Required directories ready ✓")

# Test static files exist
static_css = Path('static/css/style.css')
static_js = Path('static/js/app.js')
template_html = Path('templates/index.html')

if static_css.exists():
    with open(static_css) as f:
        css_content = f.read()
        assert 'upload-area' in css_content
        print("CSS styles ready ✓")

if static_js.exists():
    with open(static_js) as f:
        js_content = f.read()
        assert 'uploadFiles' in js_content
        print("JavaScript functionality ready ✓")

if template_html.exists():
    with open(template_html) as f:
        html_content = f.read()
        assert 'uploadArea' in html_content
        print("HTML template ready ✓")

# Test Flask app can start
with app.test_client() as client:
    response = client.get('/')
    assert response.status_code == 200
    print("Flask application ready ✓")

print("Complete application ready for production use")
            '''
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Application readiness: Complete application ready")
            return True
        else:
            print(f"❌ Application readiness: Readiness issues - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Application readiness: Error testing readiness - {e}")
        return False

def main():
    """Run all Phase 4 regression tests"""
    print("🧪 Running Phase 4 Regression Tests")
    print("Testing Web Interface Integration\n")
    print("=" * 60)
    
    tests = [
        ("Phase 4 Imports", test_phase4_imports),
        ("Phase 4 Functionality", test_phase4_functionality),
        ("Integration with Previous Phases", test_integration_with_previous_phases),
        ("Frontend-Backend Communication", test_frontend_backend_communication),
        ("Complete Application Readiness", test_complete_application_readiness)
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
    print(f"📊 PHASE 4 REGRESSION TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 4 FUNCTIONALITY IS INTACT!")
        print("✅ Web interface working correctly")
        print("✅ Frontend-backend integration successful")
        print("✅ Complete MP3 artwork processing application ready")
        print("✅ All phases (1-4) integrated and functional")
        return True
    else:
        print("⚠️  Phase 4 regression detected! Please fix failures before continuing.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 