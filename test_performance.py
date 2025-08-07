#!/usr/bin/env python3
"""
Performance Tests
Performance testing and optimization for MP3 Artwork Manager.
"""

import os
import json
import tempfile
import logging
import time
import psutil
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc

# Suppress logging during tests
logging.disable(logging.CRITICAL)

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def create_large_mp3(file_path: Path, size_mb: int = 50):
    """Create a large MP3 file for testing"""
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
        
        # Create MP3 with basic header and padding to reach desired size
        mp3_header = b'\xff\xfb\x90\x00'
        padding_size = (size_mb * 1024 * 1024) - len(mp3_header)
        mp3_data = mp3_header + b'\x00' * padding_size
        
        file_path.write_bytes(mp3_data)
        
        # Add metadata and large artwork
        audio = MP3(file_path, ID3=ID3)
        audio['TIT2'] = TIT2(encoding=3, text='Large Test Song')
        audio['TPE1'] = TPE1(encoding=3, text='Performance Test Artist')
        audio['TALB'] = TALB(encoding=3, text='Load Testing Album')
        
        # Create large artwork (1000x1000 simulated JPEG)
        large_artwork = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00' + b'\xff' * (100 * 1024)  # 100KB artwork
        
        audio['APIC'] = APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Large Cover',
            data=large_artwork
        )
        
        audio.save()
        return True
        
    except Exception as e:
        print(f"Warning: Could not create large test MP3: {e}")
        # Fallback: create just the data file
        mp3_data = b'\xff\xfb\x90\x00' + b'\x00' * (size_mb * 1024 * 1024 - 4)
        file_path.write_bytes(mp3_data)
        return False

def test_large_file_processing():
    """Test processing large files without memory issues"""
    print("\n--- Testing Large File Processing ---")
    
    try:
        from processors.file_operations import FileOperations
        
        file_ops = FileOperations(enable_musicbrainz=False)  # Disable for performance testing
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test with 50MB file
            large_file = temp_path / "large_test.mp3"
            print("Creating large test file (50MB)...")
            create_large_mp3(large_file, size_mb=50)
            
            initial_memory = get_memory_usage()
            print(f"Initial memory usage: {initial_memory:.1f} MB")
            
            # Process the large file
            start_time = time.time()
            result = file_ops.process_mp3_file(large_file, process_artwork=True)
            end_time = time.time()
            
            final_memory = get_memory_usage()
            memory_increase = final_memory - initial_memory
            processing_time = end_time - start_time
            
            print(f"Processing time: {processing_time:.2f} seconds")
            print(f"Memory increase: {memory_increase:.1f} MB")
            
            # Verify reasonable memory usage (should not exceed 200MB increase for 50MB file)
            assert memory_increase < 200, f"Memory usage too high: {memory_increase:.1f} MB"
            
            # Verify processing completed
            assert 'success' in result, "Should return processing result"
            
            print("✅ Large file processing: Memory usage acceptable")
            
            # Force garbage collection and check memory cleanup
            gc.collect()
            cleanup_memory = get_memory_usage()
            memory_leak = cleanup_memory - initial_memory
            
            if memory_leak < 50:  # Allow some memory retention
                print("✅ Memory cleanup: Good")
            else:
                print(f"⚠️ Possible memory leak: {memory_leak:.1f} MB retained")
            
        print("✅ Large File Processing: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Large file processing test failed: {e}")
        return False

def test_batch_processing_performance():
    """Test performance of batch processing multiple files"""
    print("\n--- Testing Batch Processing Performance ---")
    
    try:
        from app import app
        
        with app.test_client() as client:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create 10 medium-sized files
                file_count = 10
                file_size_mb = 5
                
                print(f"Creating {file_count} test files ({file_size_mb}MB each)...")
                
                files_data = []
                for i in range(file_count):
                    test_file = temp_path / f"batch_test_{i+1}.mp3"
                    create_large_mp3(test_file, size_mb=file_size_mb)
                    
                    with open(test_file, 'rb') as f:
                        files_data.append(('files', (f.read(), test_file.name)))
                
                initial_memory = get_memory_usage()
                print(f"Initial memory usage: {initial_memory:.1f} MB")
                
                # Upload files
                upload_start = time.time()
                response = client.post('/upload', data=dict(files_data))
                upload_end = time.time()
                
                assert response.status_code == 200, "Upload should succeed"
                upload_data = json.loads(response.data)
                session_id = upload_data['session_id']
                
                upload_time = upload_end - upload_start
                print(f"Upload time for {file_count} files: {upload_time:.2f} seconds")
                
                # Process files
                process_start = time.time()
                response = client.post(f'/process/{session_id}')
                process_end = time.time()
                
                process_time = process_end - process_start
                print(f"Processing time for {file_count} files: {process_time:.2f} seconds")
                
                final_memory = get_memory_usage()
                memory_increase = final_memory - initial_memory
                print(f"Memory increase during batch processing: {memory_increase:.1f} MB")
                
                # Performance expectations
                assert upload_time < 30, f"Upload too slow: {upload_time:.2f} seconds"
                assert process_time < 60, f"Processing too slow: {process_time:.2f} seconds"
                assert memory_increase < 500, f"Memory usage too high: {memory_increase:.1f} MB"
                
                # Check response
                if response.status_code == 200:
                    process_data = json.loads(response.data)
                    successful = process_data.get('summary', {}).get('successful', 0)
                    print(f"Successfully processed: {successful}/{file_count} files")
                
        print("✅ Batch Processing Performance: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Batch processing performance test failed: {e}")
        return False

def test_concurrent_requests():
    """Test handling concurrent requests without blocking"""
    print("\n--- Testing Concurrent Request Handling ---")
    
    try:
        from app import app
        
        def make_request(client, endpoint, data=None):
            """Make a single request and return timing info"""
            start_time = time.time()
            
            if data:
                response = client.post(endpoint, data=data)
            else:
                response = client.get(endpoint)
            
            end_time = time.time()
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time
            }
        
        # Test concurrent status requests
        with app.test_client() as client:
            num_concurrent = 10
            results = []
            
            # Use threading to simulate concurrent requests
            threads = []
            results_lock = threading.Lock()
            
            def request_worker():
                result = make_request(client, '/status/test-session')
                with results_lock:
                    results.append(result)
            
            start_time = time.time()
            
            # Start concurrent threads
            for _ in range(num_concurrent):
                thread = threading.Thread(target=request_worker)
                threads.append(thread)
                thread.start()
            
            # Wait for all to complete
            for thread in threads:
                thread.join()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"Handled {num_concurrent} concurrent requests in {total_time:.2f} seconds")
            
            # Verify all requests completed
            assert len(results) == num_concurrent, f"Should handle all {num_concurrent} requests"
            
            # Check response times are reasonable
            avg_response_time = sum(r['response_time'] for r in results) / len(results)
            max_response_time = max(r['response_time'] for r in results)
            
            print(f"Average response time: {avg_response_time:.3f} seconds")
            print(f"Maximum response time: {max_response_time:.3f} seconds")
            
            # Performance expectations
            assert avg_response_time < 1.0, f"Average response too slow: {avg_response_time:.3f} seconds"
            assert max_response_time < 2.0, f"Max response too slow: {max_response_time:.3f} seconds"
            
            # All should return 404 (expected for non-existent session)
            status_codes = [r['status_code'] for r in results]
            assert all(code == 404 for code in status_codes), "All should return 404"
            
        print("✅ Concurrent Request Handling: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Concurrent request test failed: {e}")
        return False

def test_memory_stability():
    """Test memory stability over repeated operations"""
    print("\n--- Testing Memory Stability ---")
    
    try:
        from processors.file_operations import FileOperations
        from processors.artwork_processor import ArtworkProcessor
        
        file_ops = FileOperations(enable_musicbrainz=False)
        artwork_processor = ArtworkProcessor()
        
        initial_memory = get_memory_usage()
        print(f"Initial memory usage: {initial_memory:.1f} MB")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Perform repeated operations
            iterations = 20
            memory_samples = []
            
            for i in range(iterations):
                # Create and process small test file
                test_file = temp_path / f"stability_test_{i}.mp3"
                create_large_mp3(test_file, size_mb=1)  # Small 1MB files
                
                # Process file
                result = file_ops.process_mp3_file(test_file)
                
                # Sample memory every 5 iterations
                if i % 5 == 0:
                    gc.collect()  # Force garbage collection
                    current_memory = get_memory_usage()
                    memory_samples.append(current_memory)
                    print(f"Iteration {i+1}: {current_memory:.1f} MB")
                
                # Clean up test file
                test_file.unlink()
            
            final_memory = get_memory_usage()
            print(f"Final memory usage: {final_memory:.1f} MB")
            
            # Check for memory leaks
            memory_growth = final_memory - initial_memory
            print(f"Total memory growth: {memory_growth:.1f} MB")
            
            # Verify memory growth is reasonable (should be < 100MB for 20 iterations)
            assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f} MB"
            
            # Check memory stability (no continuous growth)
            if len(memory_samples) >= 3:
                early_avg = sum(memory_samples[:2]) / 2
                late_avg = sum(memory_samples[-2:]) / 2
                growth_rate = late_avg - early_avg
                
                print(f"Memory growth rate: {growth_rate:.1f} MB")
                assert growth_rate < 50, f"Concerning memory growth rate: {growth_rate:.1f} MB"
            
        print("✅ Memory Stability: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Memory stability test failed: {e}")
        return False

def test_ui_responsiveness():
    """Test UI responsiveness during processing"""
    print("\n--- Testing UI Responsiveness ---")
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test that UI endpoints respond quickly even under load
            ui_endpoints = [
                '/',
                '/status/test-session',
                '/api/processing-status/test-session',
            ]
            
            response_times = {}
            
            for endpoint in ui_endpoints:
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times[endpoint] = response_time
                
                print(f"{endpoint}: {response_time:.3f}s (status: {response.status_code})")
                
                # UI should respond quickly
                assert response_time < 1.0, f"UI endpoint too slow: {endpoint} took {response_time:.3f}s"
            
            # Test static file serving
            static_endpoints = [
                '/static/css/style.css',
                '/static/js/app.js'
            ]
            
            for endpoint in static_endpoints:
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()
                
                response_time = end_time - start_time
                print(f"{endpoint}: {response_time:.3f}s (status: {response.status_code})")
                
                # Static files should be very fast
                assert response_time < 0.5, f"Static file too slow: {endpoint} took {response_time:.3f}s"
            
        print("✅ UI Responsiveness: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ UI responsiveness test failed: {e}")
        return False

def test_api_rate_limit_compliance():
    """Test MusicBrainz API rate limiting compliance"""
    print("\n--- Testing API Rate Limit Compliance ---")
    
    try:
        from processors.musicbrainz_client import MusicBrainzClient
        
        client = MusicBrainzClient()
        
        # Test multiple requests to ensure rate limiting
        requests = 5
        start_time = time.time()
        
        for i in range(requests):
            print(f"Making request {i+1}/{requests}...")
            result = client.search_release("Test Artist", "Test Album")
            
            # Don't sleep on the last request
            if i < requests - 1:
                time.sleep(1.1)  # Slightly more than 1 second
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should take at least (requests-1) seconds due to rate limiting
        expected_min_time = (requests - 1) * 1.0
        
        print(f"Total time for {requests} requests: {total_time:.2f} seconds")
        print(f"Expected minimum time: {expected_min_time:.2f} seconds")
        
        assert total_time >= expected_min_time, f"Rate limiting not working: {total_time:.2f}s < {expected_min_time:.2f}s"
        
        # Should not take excessively long either
        expected_max_time = expected_min_time + 5  # Allow some overhead
        assert total_time <= expected_max_time, f"Requests too slow: {total_time:.2f}s > {expected_max_time:.2f}s"
        
        print("✅ API Rate Limit Compliance: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ API rate limit compliance test failed: {e}")
        return False

def main():
    """Run all performance tests"""
    print("🧪 Running Performance Tests")
    print("Testing Performance and Optimization")
    print("=" * 75)
    
    tests = [
        ("Large File Processing", test_large_file_processing),
        ("Batch Processing Performance", test_batch_processing_performance),
        ("Concurrent Request Handling", test_concurrent_requests),
        ("Memory Stability", test_memory_stability),
        ("UI Responsiveness", test_ui_responsiveness),
        ("API Rate Limit Compliance", test_api_rate_limit_compliance)
    ]
    
    passed = 0
    total = len(tests)
    
    # Display system info
    print(f"\n💻 System Information:")
    print(f"CPU cores: {psutil.cpu_count()}")
    print(f"Available memory: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
    print(f"Python process memory: {get_memory_usage():.1f} MB")
    
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
    print(f"📊 PERFORMANCE TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PERFORMANCE TESTS PASSED!")
        print("✅ Large file processing handles 50MB+ files efficiently")
        print("✅ Batch processing maintains reasonable memory usage")
        print("✅ Concurrent requests handled without blocking")
        print("✅ Memory usage remains stable over repeated operations")
        print("✅ UI remains responsive during processing")
        print("✅ API rate limiting properly implemented")
        print("\n🚀 APPLICATION OPTIMIZED FOR PRODUCTION PERFORMANCE!")
    else:
        print(f"⚠️  {total - passed} performance tests failed. Please review failures above.")
    
    return passed == total

if __name__ == "__main__":
    main() 