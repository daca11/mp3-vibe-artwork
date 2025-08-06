#!/usr/bin/env python3
"""
Test Module for Artwork Processor
Tests image validation, resizing, and optimization functionality.
"""

import io
import sys
from PIL import Image
from processors.artwork_processor import ArtworkProcessor

def create_test_image(width: int, height: int, format: str = 'JPEG', color: str = 'red') -> bytes:
    """Create a test image with specified dimensions and format"""
    img = Image.new('RGB', (width, height), color)
    buffer = io.BytesIO()
    
    if format == 'JPEG':
        img.save(buffer, format='JPEG', quality=95)
    elif format == 'PNG':
        img.save(buffer, format='PNG')
    
    return buffer.getvalue()

def create_large_test_image(width: int, height: int, target_size_kb: int = 600) -> bytes:
    """Create a large test image that exceeds size limits"""
    # Create image with noise pattern to make it less compressible
    img = Image.new('RGB', (width, height))
    pixels = []
    
    # Use a random-like pattern to prevent compression
    import random
    random.seed(42)  # Consistent results for testing
    
    for y in range(height):
        for x in range(width):
            # Create a very noisy pattern that doesn't compress well
            r = random.randint(0, 255)
            g = random.randint(0, 255) 
            b = random.randint(0, 255)
            pixels.append((r, g, b))
    
    img.putdata(pixels)
    
    # Save with maximum quality to ensure large file size
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=100, optimize=False)
    data = buffer.getvalue()
    
    # If still not large enough, create a larger image
    if len(data) < target_size_kb * 1024:
        return create_large_test_image(width * 2, height, target_size_kb)
    
    return data

def test_artwork_validation():
    """Test artwork validation against Traktor specifications"""
    print("Testing artwork validation...")
    
    processor = ArtworkProcessor()
    
    # Test valid artwork (within specifications)
    valid_image = create_test_image(400, 300, 'JPEG')
    is_valid, issues = processor.validate_artwork(valid_image)
    
    if is_valid and len(issues) == 0:
        print("✅ Valid artwork validation: Correctly identified compliant image")
    else:
        print(f"❌ Valid artwork validation: Expected valid, got issues: {issues}")
        return False
    
    # Test oversized dimensions
    oversized_image = create_test_image(800, 600, 'JPEG')
    is_valid, issues = processor.validate_artwork(oversized_image)
    
    if not is_valid and any("Width too large" in issue for issue in issues):
        print("✅ Oversized validation: Correctly detected width issue")
    else:
        print(f"❌ Oversized validation: Expected width issue, got: {issues}")
        return False
    
    # Test file size too large
    large_image = create_large_test_image(500, 500, target_size_kb=600)
    print(f"  Created large image: {len(large_image)} bytes ({len(large_image)/1024:.1f} KB)")
    is_valid, issues = processor.validate_artwork(large_image)
    
    if not is_valid and any("File size too large" in issue for issue in issues):
        print("✅ File size validation: Correctly detected size issue")
    else:
        print(f"❌ File size validation: Expected size issue, got: {issues}")
        print(f"  Image size: {len(large_image)} bytes, limit: {processor.MAX_FILE_SIZE} bytes")
        return False
    
    # Test corrupted image data
    corrupted_data = b"This is not image data"
    is_valid, issues = processor.validate_artwork(corrupted_data)
    
    if not is_valid and any("Invalid or corrupted" in issue for issue in issues):
        print("✅ Corrupted data validation: Correctly detected corrupted image")
    else:
        print(f"❌ Corrupted data validation: Expected corruption issue, got: {issues}")
        return False
    
    return True

def test_image_info():
    """Test image information extraction"""
    print("\nTesting image information extraction...")
    
    processor = ArtworkProcessor()
    
    # Test JPEG image info
    jpeg_image = create_test_image(300, 200, 'JPEG')
    info = processor.get_image_info(jpeg_image)
    
    expected_keys = {'format', 'mode', 'width', 'height', 'size_bytes', 'has_transparency', 'color_mode', 'error'}
    
    if set(info.keys()) == expected_keys:
        print("✅ Image info keys: All expected keys present")
    else:
        print(f"❌ Image info keys: Expected {expected_keys}, got {set(info.keys())}")
        return False
    
    if info['format'] == 'JPEG' and info['width'] == 300 and info['height'] == 200:
        print("✅ JPEG image info: Correct format and dimensions")
    else:
        print(f"❌ JPEG image info: Expected JPEG 300x200, got {info['format']} {info['width']}x{info['height']}")
        return False
    
    # Test PNG image info
    png_image = create_test_image(150, 150, 'PNG')
    png_info = processor.get_image_info(png_image)
    
    if png_info['format'] == 'PNG' and png_info['width'] == 150 and png_info['height'] == 150:
        print("✅ PNG image info: Correct format and dimensions")
    else:
        print(f"❌ PNG image info: Expected PNG 150x150, got {png_info['format']} {png_info['width']}x{png_info['height']}")
        return False
    
    return True

def test_image_resizing():
    """Test image resizing while maintaining aspect ratio"""
    print("\nTesting image resizing...")
    
    processor = ArtworkProcessor()
    
    # Test resizing oversized image
    large_image = create_test_image(1000, 800, 'JPEG')
    resized_data, processing_info = processor.resize_and_optimize(large_image)
    
    if processing_info['resized']:
        print("✅ Resizing detection: Correctly identified need to resize")
    else:
        print("❌ Resizing detection: Should have detected need to resize")
        return False
    
    # Check new dimensions
    final_width, final_height = processing_info['final_dimensions']
    
    if final_width <= 500 and final_height <= 500:
        print(f"✅ Dimension compliance: Resized to {final_width}x{final_height}")
    else:
        print(f"❌ Dimension compliance: Final size {final_width}x{final_height} exceeds 500x500")
        return False
    
    # Check aspect ratio preservation
    original_ratio = 1000 / 800  # 1.25
    final_ratio = final_width / final_height
    ratio_diff = abs(original_ratio - final_ratio)
    
    if ratio_diff < 0.01:  # Allow small floating point differences
        print("✅ Aspect ratio: Maintained during resize")
    else:
        print(f"❌ Aspect ratio: Changed from {original_ratio:.3f} to {final_ratio:.3f}")
        return False
    
    # Test that small images are not resized
    small_image = create_test_image(200, 150, 'JPEG')
    small_resized_data, small_processing_info = processor.resize_and_optimize(small_image)
    
    if not small_processing_info['resized']:
        print("✅ Small image handling: Did not resize compliant image")
    else:
        print("❌ Small image handling: Should not resize images within limits")
        return False
    
    return True

def test_file_size_optimization():
    """Test file size optimization"""
    print("\nTesting file size optimization...")
    
    processor = ArtworkProcessor()
    
    # Create a large image that needs optimization
    large_image = create_large_test_image(500, 500, target_size_kb=700)
    original_size = len(large_image)
    
    print(f"  Original size: {original_size} bytes ({original_size/1024:.1f} KB)")
    
    optimized_data, processing_info = processor.resize_and_optimize(large_image)
    optimized_size = len(optimized_data)
    
    print(f"  Optimized size: {optimized_size} bytes ({optimized_size/1024:.1f} KB)")
    
    if optimized_size <= processor.MAX_FILE_SIZE:
        print("✅ Size optimization: Reduced file size to meet specifications")
    else:
        print(f"❌ Size optimization: Final size {optimized_size} still exceeds {processor.MAX_FILE_SIZE}")
        return False
    
    if optimized_size < original_size:
        print("✅ Size reduction: Optimized image is smaller than original")
    else:
        print(f"❌ Size reduction: Optimized size {optimized_size} not smaller than original {original_size}")
        return False
    
    # Check that quality adjustments were made
    if len(processing_info['quality_adjustments']) > 0:
        print("✅ Quality adjustments: Optimization steps recorded")
    else:
        print("❌ Quality adjustments: No optimization steps recorded")
        return False
    
    return True

def test_format_handling():
    """Test handling of different image formats"""
    print("\nTesting format handling...")
    
    processor = ArtworkProcessor()
    
    # Test PNG to JPEG conversion if needed
    png_image = create_test_image(400, 300, 'PNG')
    jpeg_result, processing_info = processor.resize_and_optimize(png_image, target_format='JPEG')
    
    # Verify the result is JPEG
    result_info = processor.get_image_info(jpeg_result)
    
    if result_info['format'] == 'JPEG':
        print("✅ Format conversion: Successfully converted PNG to JPEG")
    else:
        print(f"❌ Format conversion: Expected JPEG, got {result_info['format']}")
        return False
    
    # Test keeping original format when it's supported
    jpeg_image = create_test_image(300, 200, 'JPEG')
    jpeg_result, processing_info = processor.resize_and_optimize(jpeg_image)
    
    result_info = processor.get_image_info(jpeg_result)
    
    if result_info['format'] == 'JPEG':
        print("✅ Format preservation: Maintained JPEG format")
    else:
        print(f"❌ Format preservation: Expected JPEG, got {result_info['format']}")
        return False
    
    return True

def test_complete_processing_pipeline():
    """Test the complete artwork processing pipeline"""
    print("\nTesting complete processing pipeline...")
    
    processor = ArtworkProcessor()
    
    # Test with compliant image (should not be processed)
    compliant_image = create_test_image(300, 200, 'JPEG')
    result = processor.process_artwork(compliant_image)
    
    if result['is_compliant'] and not result['needs_processing']:
        print("✅ Compliant image pipeline: Correctly identified compliant artwork")
    else:
        print(f"❌ Compliant image pipeline: Expected compliant, got: {result}")
        return False
    
    # Test with non-compliant image (should be processed)
    non_compliant_image = create_test_image(800, 600, 'JPEG')
    result = processor.process_artwork(non_compliant_image, force_compliance=True)
    
    if result['needs_processing'] and result['is_compliant']:
        print("✅ Non-compliant image pipeline: Successfully processed to compliance")
    else:
        print(f"❌ Non-compliant image pipeline: Processing failed: {result}")
        return False
    
    # Check that validation issues were recorded
    if len(result['validation_issues']) > 0:
        print("✅ Validation issues: Correctly recorded original issues")
    else:
        print("❌ Validation issues: Should have recorded original validation issues")
        return False
    
    # Check that processing info is available
    expected_processing_keys = {'original_size_bytes', 'final_size_bytes', 'original_dimensions', 'final_dimensions'}
    if all(key in result['processing_info'] for key in expected_processing_keys):
        print("✅ Processing info: All expected processing information available")
    else:
        print(f"❌ Processing info: Missing processing information")
        return False
    
    return True

def main():
    """Run all artwork processor tests"""
    print("🧪 Running Artwork Processor Tests\n")
    print("=" * 60)
    
    tests = [
        ("Artwork Validation", test_artwork_validation),
        ("Image Information", test_image_info),
        ("Image Resizing", test_image_resizing),
        ("File Size Optimization", test_file_size_optimization),
        ("Format Handling", test_format_handling),
        ("Complete Processing Pipeline", test_complete_processing_pipeline)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 ARTWORK PROCESSOR TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL ARTWORK PROCESSOR TESTS PASSED!")
        print("✅ Phase 2.2 Basic Image Processing functionality is working")
        return True
    else:
        print("⚠️  Some artwork processor tests failed. Please review failures above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 