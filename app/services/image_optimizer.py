"""
Image Optimization Service for MP3 Artwork Manager
Handles image resizing, compression, and format conversion
"""
import os
import tempfile
from PIL import Image, ImageOps
from flask import current_app
import io


class ImageOptimizationError(Exception):
    """Custom exception for image optimization errors"""
    pass


class ImageOptimizer:
    """Service for optimizing artwork images"""
    
    def __init__(self):
        self.max_width = current_app.config.get('MAX_ARTWORK_WIDTH', 500)
        self.max_height = current_app.config.get('MAX_ARTWORK_HEIGHT', 500)
        self.max_file_size = current_app.config.get('MAX_ARTWORK_SIZE', 500 * 1024)  # 500KB
        self.allowed_formats = current_app.config.get('ALLOWED_ARTWORK_FORMATS', ['JPEG', 'PNG'])
    
    def optimize_image(self, input_path, output_path=None, target_format='JPEG', quality=95):
        """
        Optimize an image according to the requirements:
        - Max dimensions: 500x500px
        - Max file size: 500KB
        - Format: JPEG or PNG
        - Maintain aspect ratio
        
        Returns: dict with optimization results
        """
        try:
            # Open the original image
            with Image.open(input_path) as img:
                # Convert RGBA to RGB if saving as JPEG
                if target_format.upper() == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Get original dimensions
                original_width, original_height = img.size
                original_size = os.path.getsize(input_path)
                
                # Check if resizing is needed
                needs_resize = (original_width > self.max_width or 
                              original_height > self.max_height)
                
                optimized_img = img.copy()
                
                # Resize if needed, maintaining aspect ratio
                if needs_resize:
                    optimized_img = self._resize_image(optimized_img)
                
                # Save with compression and check file size
                if output_path is None:
                    output_path = self._generate_temp_path(target_format)
                
                # Try different quality levels to meet file size requirement
                final_quality = self._optimize_file_size(
                    optimized_img, output_path, target_format, quality
                )
                
                # Get final image info
                final_width, final_height = optimized_img.size
                final_size = os.path.getsize(output_path)
                
                optimization_result = {
                    'success': True,
                    'input_path': input_path,
                    'output_path': output_path,
                    'original_dimensions': {'width': original_width, 'height': original_height},
                    'final_dimensions': {'width': final_width, 'height': final_height},
                    'original_size': original_size,
                    'final_size': final_size,
                    'compression_ratio': final_size / original_size if original_size > 0 else 1,
                    'format': target_format,
                    'quality': final_quality,
                    'was_resized': needs_resize,
                    'size_reduction': original_size - final_size
                }
                
                current_app.logger.info(
                    f"Image optimized: {original_width}x{original_height} ({original_size} bytes) -> "
                    f"{final_width}x{final_height} ({final_size} bytes), quality: {final_quality}"
                )
                
                return optimization_result
                
        except Exception as e:
            error_msg = f"Image optimization failed for {input_path}: {str(e)}"
            current_app.logger.error(error_msg)
            raise ImageOptimizationError(error_msg)
    
    def _resize_image(self, img):
        """Resize image maintaining aspect ratio"""
        # Calculate new dimensions maintaining aspect ratio
        img.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
        return img
    
    def _optimize_file_size(self, img, output_path, format_name, initial_quality=95):
        """Optimize image file size by adjusting quality"""
        current_quality = initial_quality
        min_quality = 60  # Don't go below this quality
        
        while current_quality >= min_quality:
            # Save with current quality
            save_kwargs = {'format': format_name}
            
            if format_name.upper() == 'JPEG':
                save_kwargs.update({
                    'quality': current_quality,
                    'optimize': True,
                    'progressive': True
                })
            elif format_name.upper() == 'PNG':
                save_kwargs.update({
                    'optimize': True,
                    'compress_level': 9
                })
            
            img.save(output_path, **save_kwargs)
            
            # Check file size
            file_size = os.path.getsize(output_path)
            
            if file_size <= self.max_file_size:
                current_app.logger.debug(f"File size target met at quality {current_quality}: {file_size} bytes")
                return current_quality
            
            # Reduce quality and try again
            current_quality -= 5
            current_app.logger.debug(f"File size {file_size} too large, reducing quality to {current_quality}")
        
        # If we can't meet the size requirement, save with minimum quality
        current_app.logger.warning(f"Could not meet file size requirement, using minimum quality {min_quality}")
        return min_quality
    
    def _generate_temp_path(self, format_name):
        """Generate temporary file path for optimized image"""
        extension = '.jpg' if format_name.upper() == 'JPEG' else '.png'
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f'_optimized{extension}',
            dir=current_app.config['TEMP_FOLDER']
        )
        temp_file.close()
        return temp_file.name
    
    def create_thumbnail(self, input_path, thumbnail_path=None, size=(150, 150)):
        """Create thumbnail for preview purposes"""
        try:
            with Image.open(input_path) as img:
                # Create thumbnail maintaining aspect ratio
                img_copy = img.copy()
                img_copy.thumbnail(size, Image.Resampling.LANCZOS)
                
                if thumbnail_path is None:
                    thumbnail_path = self._generate_temp_path('JPEG')
                
                # Save as JPEG for thumbnails
                if img_copy.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img_copy.size, (255, 255, 255))
                    if img_copy.mode == 'P':
                        img_copy = img_copy.convert('RGBA')
                    background.paste(img_copy, mask=img_copy.split()[-1] if img_copy.mode == 'RGBA' else None)
                    img_copy = background
                
                img_copy.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                
                current_app.logger.info(f"Created thumbnail: {thumbnail_path}")
                return thumbnail_path
                
        except Exception as e:
            error_msg = f"Thumbnail creation failed for {input_path}: {str(e)}"
            current_app.logger.error(error_msg)
            raise ImageOptimizationError(error_msg)
    
    def get_image_info(self, image_path):
        """Get detailed information about an image"""
        try:
            with Image.open(image_path) as img:
                file_size = os.path.getsize(image_path)
                
                info = {
                    'path': image_path,
                    'dimensions': {'width': img.width, 'height': img.height},
                    'format': img.format,
                    'mode': img.mode,
                    'file_size': file_size,
                    'file_size_mb': file_size / (1024 * 1024),
                    'needs_optimization': (
                        img.width > self.max_width or 
                        img.height > self.max_height or 
                        file_size > self.max_file_size
                    ),
                    'aspect_ratio': img.width / img.height if img.height > 0 else 1
                }
                
                return info
                
        except Exception as e:
            error_msg = f"Failed to get image info for {image_path}: {str(e)}"
            current_app.logger.error(error_msg)
            raise ImageOptimizationError(error_msg)
    
    def batch_optimize(self, image_paths, output_dir=None, target_format='JPEG'):
        """Optimize multiple images in batch"""
        results = []
        
        for image_path in image_paths:
            try:
                if output_dir:
                    filename = os.path.basename(image_path)
                    name, _ = os.path.splitext(filename)
                    extension = '.jpg' if target_format.upper() == 'JPEG' else '.png'
                    output_path = os.path.join(output_dir, f"{name}_optimized{extension}")
                else:
                    output_path = None
                
                result = self.optimize_image(image_path, output_path, target_format)
                result['success'] = True
                results.append(result)
                
            except Exception as e:
                current_app.logger.error(f"Batch optimization failed for {image_path}: {str(e)}")
                results.append({
                    'input_path': image_path,
                    'success': False,
                    'error': str(e)
                })
        
        successful = sum(1 for r in results if r.get('success', False))
        current_app.logger.info(f"Batch optimization completed: {successful}/{len(image_paths)} successful")
        
        return results
    
    def convert_format(self, input_path, output_path, target_format):
        """Convert image between formats"""
        try:
            with Image.open(input_path) as img:
                # Handle transparency for JPEG conversion
                if target_format.upper() == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                save_kwargs = {'format': target_format}
                if target_format.upper() == 'JPEG':
                    save_kwargs['quality'] = 95
                    save_kwargs['optimize'] = True
                elif target_format.upper() == 'PNG':
                    save_kwargs['optimize'] = True
                
                img.save(output_path, **save_kwargs)
                
                current_app.logger.info(f"Format conversion completed: {input_path} -> {output_path} ({target_format})")
                return output_path
                
        except Exception as e:
            error_msg = f"Format conversion failed: {str(e)}"
            current_app.logger.error(error_msg)
            raise ImageOptimizationError(error_msg)
    
    def validate_image(self, image_path):
        """Validate that the file is a supported image format"""
        try:
            with Image.open(image_path) as img:
                if img.format not in self.allowed_formats and img.format not in ['JPEG', 'PNG']:
                    return False, f"Unsupported format: {img.format}"
                return True, None
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
