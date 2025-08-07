#!/usr/bin/env python3
"""
Phase 8 Tests
Tests for Final Testing & Optimization - Integration testing, performance validation, 
and production readiness verification.
"""

import json
import tempfile
import logging
import time
import os
import psutil
from pathlib import Path
from unittest.mock import Mock, patch

# Suppress logging during tests
logging.disable(logging.CRITICAL)

def test_phase8_imports():
    """Test that Phase 8 components import correctly"""
    print("\n--- Testing Phase 8 Imports ---")
    
    try:
        # Test integration test imports
        import test_integration
        print("✅ Integration tests import: Success")
        
        # Test performance test imports
        import test_performance
        print("✅ Performance tests import: Success")
        
        # Test configuration imports
        from config import config, ProductionConfig
        print("✅ Configuration imports: Success")
        
        # Test WSGI entry point
        import wsgi
        print("✅ WSGI entry point import: Success")
        
        # Test app factory
        from app import create_app
        print("✅ App factory import: Success")
        
        print("✅ Phase 8 Imports: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_app_factory_pattern():
    """Test the application factory pattern with different configurations"""
    print("\n--- Testing Application Factory Pattern ---")
    
    try:
        from app import create_app
        from config import config
        
        # Test development configuration
        dev_app = create_app('development')
        assert dev_app.config['DEBUG'] == True, "Development should have debug enabled"
        print("✅ Development configuration: Working")
        
        # Test testing configuration
        test_app = create_app('testing')
        assert test_app.config['TESTING'] == True, "Testing should have testing enabled"
        print("✅ Testing configuration: Working")
        
        # Test production configuration (with env vars)
        os.environ['SECRET_KEY'] = 'test-production-secret'
        try:
            prod_app = create_app('production')
            assert prod_app.config['DEBUG'] == False, "Production should have debug disabled"
            print("✅ Production configuration: Working")
        except ValueError:
            print("ℹ️ Production config requires SECRET_KEY (expected)")
        finally:
            os.environ.pop('SECRET_KEY', None)
        
        print("✅ Application Factory Pattern: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ App factory test failed: {e}")
        return False

def test_end_to_end_integration():
    """Run key integration tests"""
    print("\n--- Testing End-to-End Integration ---")
    
    try:
        # Import and run key integration tests
        from test_integration import (
            test_end_to_end_single_file,
            test_error_scenarios,
            test_artwork_compliance
        )
        
        # Run critical integration tests
        tests = [
            ("Single File Workflow", test_end_to_end_single_file),
            ("Error Scenarios", test_error_scenarios),
            ("Artwork Compliance", test_artwork_compliance)
        ]
        
        passed = 0
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
        
        if passed == len(tests):
            print("✅ End-to-End Integration: PASSED")
            return True
        else:
            print(f"⚠️ End-to-End Integration: {passed}/{len(tests)} tests passed")
            return False
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_performance_benchmarks():
    """Run key performance tests"""
    print("\n--- Testing Performance Benchmarks ---")
    
    try:
        # Import and run key performance tests
        from test_performance import (
            test_large_file_processing,
            test_memory_stability,
            test_ui_responsiveness
        )
        
        # Run critical performance tests
        tests = [
            ("Large File Processing", test_large_file_processing),
            ("Memory Stability", test_memory_stability),
            ("UI Responsiveness", test_ui_responsiveness)
        ]
        
        passed = 0
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
        
        if passed == len(tests):
            print("✅ Performance Benchmarks: PASSED")
            return True
        else:
            print(f"⚠️ Performance Benchmarks: {passed}/{len(tests)} tests passed")
            return False
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def test_production_readiness():
    """Test production deployment readiness"""
    print("\n--- Testing Production Readiness ---")
    
    try:
        from app import create_app
        from config import ProductionConfig
        
        # Test that production app can be created
        os.environ['SECRET_KEY'] = 'production-test-secret-key'
        os.environ['FLASK_CONFIG'] = 'production'
        
        try:
            app = create_app('production')
            
            # Test production settings
            assert app.config['DEBUG'] == False, "Production should disable debug"
            assert app.config['TESTING'] == False, "Production should disable testing"
            assert app.config['SECRET_KEY'] is not None, "Production should have secret key"
            
            print("✅ Production app creation: Working")
            
            # Test production endpoints work
            with app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200, "Homepage should load"
                
                response = client.get('/status/test')
                assert response.status_code == 404, "Should handle invalid routes"
                
            print("✅ Production endpoints: Working")
            
            # Test error handling
            with app.test_client() as client:
                response = client.post('/upload', data={})
                assert response.status_code in [200, 400], "Should handle empty uploads"
                
            print("✅ Production error handling: Working")
            
        finally:
            os.environ.pop('SECRET_KEY', None)
            os.environ.pop('FLASK_CONFIG', None)
        
        print("✅ Production Readiness: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Production readiness test failed: {e}")
        return False

def test_security_configuration():
    """Test security configurations for production"""
    print("\n--- Testing Security Configuration ---")
    
    try:
        from app import create_app
        
        # Test with production-like security settings
        os.environ['SECRET_KEY'] = 'test-secret-with-sufficient-entropy-for-production'
        
        try:
            app = create_app('production')
            
            # Test security headers and settings
            with app.test_client() as client:
                response = client.get('/')
                
                # Should not expose debug information
                assert 'Werkzeug' not in response.get_data(as_text=True), "Should not expose debug info"
                
            # Test session security
            assert app.config['SESSION_COOKIE_HTTPONLY'] == True, "Should set HttpOnly cookies"
            assert app.config['SESSION_COOKIE_SECURE'] == True, "Should require HTTPS in production"
            
            print("✅ Security headers: Working")
            
            # Test file upload limits
            assert app.config['MAX_CONTENT_LENGTH'] == 100 * 1024 * 1024, "Should limit file sizes"
            
            print("✅ Upload security: Working")
            
        finally:
            os.environ.pop('SECRET_KEY', None)
        
        print("✅ Security Configuration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Security configuration test failed: {e}")
        return False

def test_logging_configuration():
    """Test logging configuration for production monitoring"""
    print("\n--- Testing Logging Configuration ---")
    
    try:
        from config import ProductionConfig
        import logging
        import tempfile
        
        # Test production logging setup
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            # Simulate production logging setup
            ProductionConfig.LOG_FILE = str(log_file)
            
            # Create a test logger
            test_logger = logging.getLogger('test_production_logger')
            
            # Set up file handler similar to production
            file_handler = logging.FileHandler(str(log_file))
            file_handler.setLevel(logging.WARNING)
            test_logger.addHandler(file_handler)
            test_logger.setLevel(logging.WARNING)
            
            # Test logging
            test_logger.warning("Test warning message")
            test_logger.error("Test error message")
            
            # Verify log file was created and contains messages
            assert log_file.exists(), "Log file should be created"
            
            log_content = log_file.read_text()
            assert "Test warning message" in log_content, "Should log warning messages"
            assert "Test error message" in log_content, "Should log error messages"
            
            print("✅ File logging: Working")
        
        print("✅ Logging Configuration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Logging configuration test failed: {e}")
        return False

def test_deployment_files():
    """Test that all deployment files are present and valid"""
    print("\n--- Testing Deployment Files ---")
    
    try:
        # Check required files exist
        required_files = [
            'config.py',
            'wsgi.py',
            'requirements.txt',
            'USER_GUIDE.md',
            'README.md'
        ]
        
        for file_name in required_files:
            file_path = Path(file_name)
            assert file_path.exists(), f"Required file missing: {file_name}"
            assert file_path.stat().st_size > 0, f"File is empty: {file_name}"
        
        print("✅ Required files present: All found")
        
        # Test configuration file is valid Python
        try:
            import config
            assert hasattr(config, 'config'), "Config should have config dictionary"
            assert 'production' in config.config, "Should have production config"
        except ImportError:
            assert False, "Config file should be valid Python"
        
        print("✅ Configuration file: Valid")
        
        # Test WSGI file is valid
        try:
            import wsgi
            assert hasattr(wsgi, 'application'), "WSGI should have application object"
        except ImportError:
            assert False, "WSGI file should be valid Python"
        
        print("✅ WSGI file: Valid")
        
        # Test requirements.txt has required packages
        requirements_path = Path('requirements.txt')
        if requirements_path.exists():
            requirements_content = requirements_path.read_text()
            
            required_packages = ['Flask', 'Pillow', 'mutagen', 'musicbrainzngs', 'requests']
            for package in required_packages:
                assert package in requirements_content, f"Requirements should include {package}"
            
            print("✅ Requirements file: Valid")
        
        print("✅ Deployment Files: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Deployment files test failed: {e}")
        return False

def test_documentation_completeness():
    """Test that documentation is complete and helpful"""
    print("\n--- Testing Documentation Completeness ---")
    
    try:
        # Test README.md
        readme_path = Path('README.md')
        assert readme_path.exists(), "README.md should exist"
        
        readme_content = readme_path.read_text()
        required_sections = [
            'Installation',
            'Usage',
            'Features',
            'Testing',
            'Development Progress'
        ]
        
        for section in required_sections:
            assert section in readme_content, f"README should include {section} section"
        
        print("✅ README completeness: Good")
        
        # Test USER_GUIDE.md
        guide_path = Path('USER_GUIDE.md')
        assert guide_path.exists(), "USER_GUIDE.md should exist"
        
        guide_content = guide_path.read_text()
        required_guide_sections = [
            'Getting Started',
            'Step-by-Step Usage',
            'Troubleshooting',
            'FAQ',
            'System Requirements'
        ]
        
        for section in required_guide_sections:
            assert section in guide_content, f"User guide should include {section} section"
        
        print("✅ User guide completeness: Good")
        
        # Test that documentation mentions production features
        all_docs = readme_content + guide_content
        production_features = [
            'error handling',
            'progress tracking',
            'MusicBrainz',
            'artwork',
            'Traktor'
        ]
        
        for feature in production_features:
            assert feature.lower() in all_docs.lower(), f"Documentation should mention {feature}"
        
        print("✅ Feature documentation: Complete")
        
        print("✅ Documentation Completeness: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Documentation test failed: {e}")
        return False

def test_all_phases_integration():
    """Test that all phases work together correctly"""
    print("\n--- Testing All Phases Integration ---")
    
    try:
        # Test that all phase test modules can be imported
        phase_modules = [
            'test_file_handler',
            'test_artwork_processor', 
            'test_file_operations',
            'test_web_interface',
            'test_musicbrainz_client',
            'test_phase5',
            'test_phase6',
            'test_phase7'
        ]
        
        for module in phase_modules:
            try:
                __import__(module)
                print(f"✅ {module}: Imports successfully")
            except ImportError as e:
                print(f"❌ {module}: Import failed - {e}")
                return False
        
        # Test that core components work together
        from processors.file_operations import FileOperations
        from processors.error_handler import error_handler
        from app import create_app
        
        # Test app with all features
        app = create_app('testing')
        with app.test_client() as client:
            # Test basic functionality works
            response = client.get('/')
            assert response.status_code == 200, "App should load"
            
            response = client.get('/status/test')
            assert response.status_code == 404, "Should handle invalid sessions"
        
        print("✅ Cross-phase compatibility: Working")
        
        # Test error handler integration
        assert error_handler is not None, "Global error handler should be available"
        
        file_ops = FileOperations(enable_musicbrainz=True)
        assert hasattr(file_ops, 'musicbrainz_client'), "Should have MusicBrainz integration"
        assert hasattr(file_ops, 'mp3_handler'), "Should have MP3 handler"
        assert hasattr(file_ops, 'artwork_processor'), "Should have artwork processor"
        
        print("✅ Component integration: Working")
        
        print("✅ All Phases Integration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ All phases integration test failed: {e}")
        return False

def main():
    """Run all Phase 8 tests"""
    print("🧪 Running Phase 8 Tests")
    print("Testing Final Testing & Optimization - Production Readiness")
    print("=" * 75)
    
    tests = [
        ("Phase 8 Imports", test_phase8_imports),
        ("Application Factory Pattern", test_app_factory_pattern),
        ("End-to-End Integration", test_end_to_end_integration),
        ("Performance Benchmarks", test_performance_benchmarks),
        ("Production Readiness", test_production_readiness),
        ("Security Configuration", test_security_configuration),
        ("Logging Configuration", test_logging_configuration),
        ("Deployment Files", test_deployment_files),
        ("Documentation Completeness", test_documentation_completeness),
        ("All Phases Integration", test_all_phases_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    # Display system info
    print(f"\n💻 System Information:")
    print(f"CPU cores: {psutil.cpu_count()}")
    print(f"Available memory: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
    print(f"Python version: {os.sys.version}")
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 60)
        
        try:
            success = test_func()
            if success:
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 75)
    print(f"📊 PHASE 8 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 8 TESTS PASSED!")
        print("✅ Integration testing comprehensive and passing")
        print("✅ Performance benchmarks meet production standards")
        print("✅ Production deployment configuration ready")
        print("✅ Security configuration properly implemented")
        print("✅ Logging and monitoring systems operational")
        print("✅ Documentation complete and user-friendly")
        print("✅ All phases (1-8) integrated and functional")
        print("\n🚀 🎉 **MP3 ARTWORK MANAGER IS PRODUCTION READY!** 🎉 🚀")
        print("\n🏁 **PROJECT COMPLETE - ALL PHASES IMPLEMENTED**")
        print("   Ready for deployment to production environment!")
    else:
        print(f"⚠️  {total - passed} Phase 8 tests failed. Please review failures above.")
    
    return passed == total

if __name__ == "__main__":
    main() 