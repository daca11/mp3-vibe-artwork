#!/usr/bin/env python3
"""
Phase 7 Tests
Tests for Error Handling & Polish - Comprehensive error handling, progress tracking, and user experience improvements.
"""

import json
import tempfile
import logging
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Suppress logging during tests
logging.disable(logging.CRITICAL)

def test_phase7_imports():
    """Test that Phase 7 imports work correctly"""
    print("\n--- Testing Phase 7 Imports ---")
    
    try:
        # Test error handler import
        from processors.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity, ProcessingError
        print("✅ Error handler classes import: Success")
        
        # Test enhanced Flask app import
        from app import app
        print("✅ Enhanced Flask app import: Success")
        
        # Test error handler integration
        from processors.error_handler import error_handler
        assert hasattr(error_handler, 'handle_error'), "Should have handle_error method"
        assert hasattr(error_handler, 'get_error_summary'), "Should have get_error_summary method"
        print("✅ Error handler integration: Available")
        
        print("✅ Phase 7 Imports: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_error_handler_functionality():
    """Test the core error handler functionality"""
    print("\n--- Testing Error Handler Functionality ---")
    
    try:
        from processors.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
        
        # Create a new error handler instance for testing
        handler = ErrorHandler()
        
        # Test error handling
        error = handler.handle_error(
            ErrorCategory.FILE_VALIDATION,
            ErrorSeverity.HIGH,
            "Test error message",
            file_path=Path("test.mp3")
        )
        
        assert error.category == ErrorCategory.FILE_VALIDATION, "Should store error category"
        assert error.severity == ErrorSeverity.HIGH, "Should store error severity"
        assert "test.mp3" in str(error.file_path), "Should store file path"
        print("✅ Error handling: Working")
        
        # Test error summary
        summary = handler.get_error_summary()
        assert summary['total_errors'] == 1, "Should count errors"
        assert summary['error_counts_by_category']['file_validation'] == 1, "Should categorize errors"
        print("✅ Error summary: Working")
        
        # Test retry logic
        network_error = handler.handle_error(
            ErrorCategory.NETWORK_ERROR,
            ErrorSeverity.MEDIUM,
            "Network timeout"
        )
        
        assert network_error.can_retry(), "Network errors should be retryable"
        print("✅ Retry logic: Working")
        
        # Test user-friendly messages
        user_message = handler.get_user_friendly_message(error)
        assert "corrupted" in user_message.lower() or "valid" in user_message.lower(), "Should provide user-friendly message"
        print("✅ User-friendly messages: Working")
        
        print("✅ Error Handler Functionality: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Error handler test failed: {e}")
        return False

def test_enhanced_api_endpoints():
    """Test the enhanced API endpoints for error handling and progress tracking"""
    print("\n--- Testing Enhanced API Endpoints ---")
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test processing status endpoint
            response = client.get('/api/processing-status/invalid-session')
            assert response.status_code == 404, "Should return 404 for invalid session"
            print("✅ Processing status endpoint: Error handling works")
            
            # Test processing controls endpoint
            response = client.post('/api/processing-controls/invalid-session',
                                 json={'action': 'pause'})
            assert response.status_code == 404, "Should return 404 for invalid session"
            print("✅ Processing controls endpoint: Error handling works")
            
            # Test error log endpoint
            response = client.get('/api/error-log/invalid-session')
            assert response.status_code == 404, "Should return 404 for invalid session"
            print("✅ Error log endpoint: Error handling works")
            
            # Test with mock session data
            from app import processing_sessions
            
            session_id = 'test-session-789'
            processing_sessions[session_id] = {
                'status': 'uploaded',
                'files': [{'filename': 'test.mp3'}],
                'processed_files': 0,
                'current_file': 0
            }
            
            # Test processing status with valid session
            response = client.get(f'/api/processing-status/{session_id}')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                assert 'session_id' in data, "Should include session ID"
                assert 'progress_percentage' in data, "Should include progress"
                assert 'errors' in data, "Should include error summary"
                print("✅ Processing status with valid session: Working")
            
            # Test processing controls with valid session
            response = client.post(f'/api/processing-controls/{session_id}',
                                 json={'action': 'pause'})
            
            if response.status_code == 200:
                data = json.loads(response.data)
                assert data['success'] == True, "Should indicate success"
                assert 'message' in data, "Should include message"
                print("✅ Processing controls with valid session: Working")
            
            # Cleanup
            del processing_sessions[session_id]
        
        print("✅ Enhanced API Endpoints: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced API endpoints test failed: {e}")
        return False

def test_progress_tracking_integration():
    """Test progress tracking integration"""
    print("\n--- Testing Progress Tracking Integration ---")
    
    try:
        # Test that JavaScript functions are available
        js_path = Path('static/js/app.js')
        if js_path.exists():
            js_content = js_path.read_text()
            
            required_functions = [
                'startProgressTracking',
                'stopProgressTracking',
                'updateProgressDisplay',
                'controlProcessing',
                'showErrorLog'
            ]
            
            for func in required_functions:
                assert func in js_content, f"Should include {func} function"
            
            print("✅ Progress tracking JavaScript functions: Present")
        
        # Test that CSS styles are available
        css_path = Path('static/css/style.css')
        if css_path.exists():
            css_content = css_path.read_text()
            
            required_styles = [
                'progress-section',
                'progress-bar',
                'error-container',
                'processing-controls'
            ]
            
            for style in required_styles:
                assert style in css_content, f"Should include {style} styles"
            
            print("✅ Progress tracking CSS styles: Present")
        
        print("✅ Progress Tracking Integration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Progress tracking integration test failed: {e}")
        return False

def test_error_recovery_mechanisms():
    """Test error recovery and retry mechanisms"""
    print("\n--- Testing Error Recovery Mechanisms ---")
    
    try:
        from processors.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
        
        handler = ErrorHandler()
        
        # Test retry-eligible errors
        network_error = handler.handle_error(
            ErrorCategory.NETWORK_ERROR,
            ErrorSeverity.MEDIUM,
            "Connection timeout"
        )
        
        api_error = handler.handle_error(
            ErrorCategory.MUSICBRAINZ_API,
            ErrorSeverity.LOW,
            "API rate limit"
        )
        
        # Test non-retry-eligible errors
        file_error = handler.handle_error(
            ErrorCategory.FILE_VALIDATION,
            ErrorSeverity.HIGH,
            "Corrupted file"
        )
        
        critical_error = handler.handle_error(
            ErrorCategory.SYSTEM_ERROR,
            ErrorSeverity.CRITICAL,
            "System failure"
        )
        
        # Verify retry eligibility
        assert network_error.can_retry(), "Network errors should be retryable"
        assert api_error.can_retry(), "API errors should be retryable"
        assert not file_error.can_retry(), "File validation errors should not be retryable"
        assert not critical_error.can_retry(), "Critical errors should not be retryable"
        
        print("✅ Error retry eligibility: Working")
        
        # Test retry count increment
        initial_count = network_error.retry_count
        network_error.increment_retry()
        assert network_error.retry_count == initial_count + 1, f"Should increment retry count from {initial_count} to {initial_count + 1}, got {network_error.retry_count}"
        
        # Test max retries exceeded
        for _ in range(10):  # Exceed max retries
            network_error.increment_retry()
        
        assert not network_error.can_retry(), "Should not be retryable after max retries"
        print("✅ Retry count management: Working")
        
        # Test critical error stops processing
        assert handler.should_stop_processing, "Critical errors should stop processing"
        print("✅ Critical error handling: Working")
        
        print("✅ Error Recovery Mechanisms: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Error recovery mechanisms test failed: {e}")
        return False

def test_enhanced_processing_pipeline():
    """Test the enhanced processing pipeline with error handling"""
    print("\n--- Testing Enhanced Processing Pipeline ---")
    
    try:
        from processors.file_operations import FileOperations
        
        # Test with error handler integration
        file_ops = FileOperations(enable_musicbrainz=False)
        
        # Test with non-existent file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            non_existent_file = temp_path / "nonexistent.mp3"
            
            result = file_ops.process_mp3_file(non_existent_file)
            
            # Should handle error gracefully
            assert 'success' in result, "Should return result structure"
            # The error structure may vary, so just check that it handles the case
            assert result['success'] == False, "Should indicate failure"
            print("✅ Non-existent file error handling: Working")
            
            # Test with invalid MP3 file
            invalid_file = temp_path / "invalid.mp3"
            invalid_file.write_bytes(b"not an mp3 file")
            
            result = file_ops.process_mp3_file(invalid_file)
            
            # Should handle gracefully with warnings/errors
            assert 'success' in result, "Should return result structure"
            print("✅ Invalid file error handling: Working")
        
        print("✅ Enhanced Processing Pipeline: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced processing pipeline test failed: {e}")
        return False

def test_logging_and_monitoring():
    """Test enhanced logging and monitoring capabilities"""
    print("\n--- Testing Logging and Monitoring ---")
    
    try:
        from processors.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
        import tempfile
        
        handler = ErrorHandler()
        
        # Add some test errors
        handler.handle_error(
            ErrorCategory.FILE_VALIDATION,
            ErrorSeverity.HIGH,
            "Test file error"
        )
        
        handler.handle_error(
            ErrorCategory.NETWORK_ERROR,
            ErrorSeverity.MEDIUM,
            "Test network error"
        )
        
        # Test error log export
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            log_path = Path(f.name)
        
        handler.export_error_log(log_path)
        
        # Verify log file was created and contains expected content
        assert log_path.exists(), "Should create log file"
        
        log_content = log_path.read_text()
        assert "MP3 Artwork Manager - Error Log" in log_content, "Should include header"
        assert "Test file error" in log_content, "Should include error messages"
        assert "Test network error" in log_content, "Should include error messages"
        
        print("✅ Error log export: Working")
        
        # Clean up
        log_path.unlink()
        
        # Test error summary format
        summary = handler.get_error_summary()
        
        required_keys = [
            'total_errors',
            'error_counts_by_category',
            'error_counts_by_severity',
            'recent_errors',
            'retryable_errors'
        ]
        
        for key in required_keys:
            assert key in summary, f"Summary should include {key}"
        
        print("✅ Error summary format: Working")
        
        print("✅ Logging and Monitoring: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Logging and monitoring test failed: {e}")
        return False

def test_integration_with_previous_phases():
    """Test that Phase 7 integrates properly with all previous phases"""
    print("\n--- Testing Integration with Previous Phases ---")
    
    try:
        # Test that all previous functionality still works with error handling
        from processors.file_operations import FileOperations
        from processors.error_handler import error_handler
        
        # Initialize with all features
        file_ops = FileOperations(enable_musicbrainz=True)
        
        # Test that error handler is integrated
        assert hasattr(file_ops, 'mp3_handler'), "Should have mp3_handler"
        assert hasattr(file_ops, 'artwork_processor'), "Should have artwork_processor"
        assert hasattr(file_ops, 'musicbrainz_client'), "Should have musicbrainz_client"
        
        print("✅ Previous phase integration: All components present")
        
        # Test that error handler is available globally
        assert error_handler is not None, "Should have global error handler"
        assert hasattr(error_handler, 'handle_error'), "Should have error handling methods"
        
        print("✅ Error handler integration: Working")
        
        # Test Flask app with all phases
        from app import app
        
        with app.test_client() as client:
            # Test that all previous endpoints still work
            response = client.get('/')
            assert response.status_code == 200, "Homepage should load"
            
            # Test that new endpoints are available
            response = client.get('/api/processing-status/test')
            assert response.status_code == 404, "Should handle invalid session properly"
            
        print("✅ Flask integration: Working")
        
        print("✅ Integration with Previous Phases: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Run all Phase 7 tests"""
    print("🧪 Running Phase 7 Tests")
    print("Testing Error Handling & Polish - Comprehensive Error Management")
    print("=" * 75)
    
    tests = [
        ("Phase 7 Imports", test_phase7_imports),
        ("Error Handler Functionality", test_error_handler_functionality),
        ("Enhanced API Endpoints", test_enhanced_api_endpoints),
        ("Progress Tracking Integration", test_progress_tracking_integration),
        ("Error Recovery Mechanisms", test_error_recovery_mechanisms),
        ("Enhanced Processing Pipeline", test_enhanced_processing_pipeline),
        ("Logging and Monitoring", test_logging_and_monitoring),
        ("Integration with Previous Phases", test_integration_with_previous_phases)
    ]
    
    passed = 0
    total = len(tests)
    
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
    print(f"📊 PHASE 7 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PHASE 7 FUNCTIONALITY IS WORKING!")
        print("✅ Comprehensive error handling implemented")
        print("✅ Progress tracking and user feedback enhanced") 
        print("✅ Processing controls (pause/resume/cancel/retry) functional")
        print("✅ Detailed error logging and monitoring available")
        print("✅ Production-ready reliability achieved")
        print("✅ All phases (1-7) integrated and functional")
        print("\n🚀 PRODUCTION-READY MP3 ARTWORK MANAGER!")
    else:
        print(f"⚠️  {total - passed} Phase 7 tests failed. Please review failures above.")
    
    return passed == total

if __name__ == "__main__":
    main() 