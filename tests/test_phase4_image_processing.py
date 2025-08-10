"""
Unit tests for Phase 4: Image Processing & Optimization
"""
import pytest
import tempfile
import os
from PIL import Image
from app import create_app
from app.services.image_optimizer import ImageOptimizer, ImageOptimizationError


@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app('testing')
    
    # Create temporary directories for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        app.config['UPLOAD_FOLDER'] = os.path.join(temp_dir, 'uploads')
        app.config['TEMP_FOLDER'] = os.path.join(temp_dir, 'temp')
        app.config['OUTPUT_FOLDER'] = os.path.join(temp_dir, 'output')
        
        os.makedirs(app.config['UPLOAD_FOLDER'])
        os.makedirs(app.config['TEMP_FOLDER'])
        os.makedirs(app.config['OUTPUT_FOLDER'])
        
        yield app


@pytest.fixture
def large_test_image(app):
    """Create a large test image that needs optimization"""
    # Create a 1000x1000 image (larger than 500x500 requirement)
    img = Image.new('RGB', (1000, 1000), color='red')
    
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.png',
        dir=app.config['TEMP_FOLDER']
    )
    img.save(temp_file.name, 'PNG')
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def small_test_image(app):
    """Create a small test image that doesn't need optimization"""
    # Create a 300x300 image (smaller than 500x500 requirement)
    img = Image.new('RGB', (300, 300), color='blue')
    
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.jpg',
        dir=app.config['TEMP_FOLDER']
    )
    img.save(temp_file.name, 'JPEG', quality=95)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def rgba_test_image(app):
    """Create an RGBA test image for transparency testing"""
    # Create a 400x400 RGBA image with transparency
    img = Image.new('RGBA', (400, 400), color=(255, 0, 0, 128))  # Semi-transparent red
    
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.png',
        dir=app.config['TEMP_FOLDER']
    )
    img.save(temp_file.name, 'PNG')
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


class TestImageOptimizer:
    """Test image optimizer service"""
    
    def test_optimizer_creation(self, app):
        """Test creating image optimizer"""
        with app.app_context():
            optimizer = ImageOptimizer()
            assert optimizer is not None
            assert optimizer.max_width == 500
            assert optimizer.max_height == 500
            assert optimizer.max_file_size == 500 * 1024
    
    def test_get_image_info(self, app, large_test_image):
        """Test getting image information"""
        with app.app_context():
            optimizer = ImageOptimizer()
            info = optimizer.get_image_info(large_test_image)
            
            assert info['dimensions']['width'] == 1000
            assert info['dimensions']['height'] == 1000
            assert info['format'] == 'PNG'
            assert info['needs_optimization'] == True  # Should need optimization due to size
            assert info['aspect_ratio'] == 1.0  # Square image
    
    def test_get_image_info_small_image(self, app, small_test_image):
        """Test image info for small image that doesn't need optimization"""
        with app.app_context():
            optimizer = ImageOptimizer()
            info = optimizer.get_image_info(small_test_image)
            
            assert info['dimensions']['width'] == 300
            assert info['dimensions']['height'] == 300
            assert info['format'] == 'JPEG'
            # May or may not need optimization depending on file size
            assert 'needs_optimization' in info
    
    def test_optimize_large_image(self, app, large_test_image):
        """Test optimizing a large image"""
        with app.app_context():
            optimizer = ImageOptimizer()
            
            # Create output path
            output_path = os.path.join(app.config['TEMP_FOLDER'], 'optimized.jpg')
            
            result = optimizer.optimize_image(large_test_image, output_path, 'JPEG')
            
            assert result['success'] == True
            assert result['was_resized'] == True
            assert result['final_dimensions']['width'] <= 500
            assert result['final_dimensions']['height'] <= 500
            assert result['final_size'] <= 500 * 1024  # Should meet file size requirement
            assert os.path.exists(output_path)
            
            # Check aspect ratio is maintained
            original_ratio = result['original_dimensions']['width'] / result['original_dimensions']['height']
            final_ratio = result['final_dimensions']['width'] / result['final_dimensions']['height']
            assert abs(original_ratio - final_ratio) < 0.01  # Allow small floating point differences
    
    def test_optimize_small_image(self, app, small_test_image):
        """Test optimizing a small image that doesn't need resizing"""
        with app.app_context():
            optimizer = ImageOptimizer()
            
            output_path = os.path.join(app.config['TEMP_FOLDER'], 'optimized_small.jpg')
            
            result = optimizer.optimize_image(small_test_image, output_path, 'JPEG')
            
            assert result['success'] == True
            assert result['final_dimensions']['width'] == 300
            assert result['final_dimensions']['height'] == 300
            # Should not be resized since it's already small enough
            assert result['was_resized'] == False
    
    def test_rgba_to_jpeg_conversion(self, app, rgba_test_image):
        """Test converting RGBA image to JPEG (handling transparency)"""
        with app.app_context():
            optimizer = ImageOptimizer()
            
            output_path = os.path.join(app.config['TEMP_FOLDER'], 'rgba_to_jpeg.jpg')
            
            result = optimizer.optimize_image(rgba_test_image, output_path, 'JPEG')
            
            assert result['success'] == True
            assert result['format'] == 'JPEG'
            assert os.path.exists(output_path)
            
            # Check that the output is actually a JPEG
            with Image.open(output_path) as img:
                assert img.format == 'JPEG'
                assert img.mode == 'RGB'  # Should be converted from RGBA
    
    def test_validate_image_valid(self, app, small_test_image):
        """Test validating a valid image"""
        with app.app_context():
            optimizer = ImageOptimizer()
            is_valid, error = optimizer.validate_image(small_test_image)
            
            assert is_valid == True
            assert error is None
    
    def test_validate_image_invalid(self, app):
        """Test validating an invalid image file"""
        with app.app_context():
            # Create a non-image file
            text_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.txt',
                dir=app.config['TEMP_FOLDER']
            )
            text_file.write(b'This is not an image')
            text_file.close()
            
            try:
                optimizer = ImageOptimizer()
                is_valid, error = optimizer.validate_image(text_file.name)
                
                assert is_valid == False
                assert error is not None
                assert 'Invalid image file' in error
                
            finally:
                os.unlink(text_file.name)
    
    def test_batch_optimize(self, app, large_test_image, small_test_image):
        """Test batch optimization of multiple images"""
        with app.app_context():
            optimizer = ImageOptimizer()
            
            output_dir = os.path.join(app.config['TEMP_FOLDER'], 'batch_output')
            os.makedirs(output_dir, exist_ok=True)
            
            image_paths = [large_test_image, small_test_image]
            results = optimizer.batch_optimize(image_paths, output_dir, 'JPEG')
            
            assert len(results) == 2
            
            # Check that both optimizations were successful
            for result in results:
                assert result.get('success', False) == True
                assert os.path.exists(result['output_path'])
    
    def test_convert_format(self, app, rgba_test_image):
        """Test format conversion"""
        with app.app_context():
            optimizer = ImageOptimizer()
            
            output_path = os.path.join(app.config['TEMP_FOLDER'], 'converted.jpg')
            
            result_path = optimizer.convert_format(rgba_test_image, output_path, 'JPEG')
            
            assert result_path == output_path
            assert os.path.exists(output_path)
            
            # Verify the conversion
            with Image.open(output_path) as img:
                assert img.format == 'JPEG'
    
    def test_optimization_error_handling(self, app):
        """Test error handling for optimization failures"""
        with app.app_context():
            optimizer = ImageOptimizer()
            
            # Try to optimize a non-existent file
            with pytest.raises(ImageOptimizationError):
                optimizer.optimize_image('/nonexistent/file.jpg')
    
    def test_file_size_optimization(self, app):
        """Test that optimizer reduces file size to meet requirements"""
        with app.app_context():
            # Create a large image that will likely exceed 500KB
            large_img = Image.new('RGB', (2000, 2000), color='red')
            
            large_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.png',
                dir=app.config['TEMP_FOLDER']
            )
            large_img.save(large_file.name, 'PNG')
            large_file.close()
            
            try:
                optimizer = ImageOptimizer()
                output_path = os.path.join(app.config['TEMP_FOLDER'], 'size_optimized.jpg')
                
                result = optimizer.optimize_image(large_file.name, output_path, 'JPEG')
                
                assert result['success'] == True
                assert result['final_size'] <= 500 * 1024  # Should meet size requirement
                assert result['final_size'] < result['original_size']  # Should be smaller
                
            finally:
                os.unlink(large_file.name)


if __name__ == '__main__':
    pytest.main([__file__])
