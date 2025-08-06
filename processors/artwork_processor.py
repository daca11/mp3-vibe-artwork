#!/usr/bin/env python3
"""
Artwork Processor Module
Handles image validation, resizing, and optimization for Traktor 3 specifications.
"""

import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from PIL import Image, ImageEnhance
from PIL.ExifTags import TAGS

# Set up logging
logger = logging.getLogger(__name__)

class ArtworkProcessor:
    """
    Handles artwork validation, resizing, and optimization for Traktor 3 specifications.
    
    Traktor 3 Specifications:
    - Maximum dimensions: 500x500 pixels
    - Maximum file size: 500KB (512,000 bytes)
    - Supported formats: JPEG, PNG
    """
    
    # Traktor 3 artwork specifications
    MAX_WIDTH = 500
    MAX_HEIGHT = 500
    MAX_FILE_SIZE = 500 * 1024  # 500KB in bytes
    SUPPORTED_FORMATS = {'JPEG', 'PNG'}
    
    def __init__(self):
        """Initialize the artwork processor."""
        pass
    
    def validate_artwork(self, image_data: bytes, mime_type: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate artwork against Traktor 3 specifications.
        
        Args:
            image_data: Raw image bytes
            mime_type: Optional MIME type hint (e.g., 'image/jpeg')
            
        Returns:
            Tuple of (is_valid, issues_list)
            is_valid: True if artwork meets all specifications
            issues_list: List of strings describing any issues found
        """
        issues = []
        
        try:
            # Check file size
            file_size = len(image_data)
            if file_size > self.MAX_FILE_SIZE:
                issues.append(f"File size too large: {file_size} bytes (max: {self.MAX_FILE_SIZE} bytes)")
            
            # Try to open and validate the image
            try:
                with Image.open(io.BytesIO(image_data)) as img:
                    # Check format
                    if img.format not in self.SUPPORTED_FORMATS:
                        issues.append(f"Unsupported format: {img.format} (supported: {', '.join(self.SUPPORTED_FORMATS)})")
                    
                    # Check dimensions
                    width, height = img.size
                    if width > self.MAX_WIDTH:
                        issues.append(f"Width too large: {width}px (max: {self.MAX_WIDTH}px)")
                    if height > self.MAX_HEIGHT:
                        issues.append(f"Height too large: {height}px (max: {self.MAX_HEIGHT}px)")
                    
                    # Check if image is valid (can be processed)
                    img.verify()
                    
            except Exception as e:
                issues.append(f"Invalid or corrupted image data: {e}")
                
        except Exception as e:
            issues.append(f"Error validating artwork: {e}")
        
        is_valid = len(issues) == 0
        logger.debug(f"Artwork validation: valid={is_valid}, issues={issues}")
        
        return is_valid, issues
    
    def get_image_info(self, image_data: bytes) -> Dict[str, Union[str, int, float, None]]:
        """
        Get comprehensive information about an image.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Dictionary with image information:
            {
                'format': str,
                'mode': str,
                'width': int,
                'height': int,
                'size_bytes': int,
                'has_transparency': bool,
                'color_mode': str,
                'error': str or None
            }
        """
        info = {
            'format': None,
            'mode': None,
            'width': 0,
            'height': 0,
            'size_bytes': len(image_data),
            'has_transparency': False,
            'color_mode': None,
            'error': None
        }
        
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                info['format'] = img.format
                info['mode'] = img.mode
                info['width'], info['height'] = img.size
                info['has_transparency'] = img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                info['color_mode'] = img.mode
                
        except Exception as e:
            info['error'] = str(e)
            logger.error(f"Error getting image info: {e}")
        
        return info
    
    def resize_and_optimize(self, image_data: bytes, target_format: str = None) -> Tuple[bytes, Dict[str, Union[str, int]]]:
        """
        Resize and optimize an image to meet Traktor 3 specifications.
        
        Args:
            image_data: Raw image bytes
            target_format: Target format ('JPEG' or 'PNG'). If None, keeps original format
            
        Returns:
            Tuple of (optimized_image_bytes, processing_info)
            processing_info: Dict with details about the optimization process
        """
        processing_info = {
            'original_size_bytes': len(image_data),
            'original_dimensions': None,
            'final_size_bytes': 0,
            'final_dimensions': None,
            'format_changed': False,
            'resized': False,
            'quality_adjustments': [],
            'error': None
        }
        
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                processing_info['original_dimensions'] = img.size
                original_format = img.format
                
                # Determine target format
                if target_format is None:
                    target_format = original_format if original_format in self.SUPPORTED_FORMATS else 'JPEG'
                
                if target_format not in self.SUPPORTED_FORMATS:
                    target_format = 'JPEG'  # Default to JPEG
                
                processing_info['format_changed'] = (target_format != original_format)
                
                # Convert image mode if necessary for target format
                if target_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                    # Convert RGBA/LA/P to RGB for JPEG (remove transparency)
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                    else:
                        background.paste(img)
                    img = background
                elif target_format == 'PNG' and img.mode not in ('RGBA', 'RGB', 'L', 'LA'):
                    img = img.convert('RGBA')
                
                # Resize if necessary
                width, height = img.size
                if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
                    # Calculate new size maintaining aspect ratio
                    ratio = min(self.MAX_WIDTH / width, self.MAX_HEIGHT / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    
                    # Use high-quality resampling
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    processing_info['resized'] = True
                    processing_info['final_dimensions'] = (new_width, new_height)
                else:
                    processing_info['final_dimensions'] = (width, height)
                
                # Optimize file size
                optimized_data = self._optimize_file_size(img, target_format, processing_info)
                processing_info['final_size_bytes'] = len(optimized_data)
                
                logger.info(f"Image optimization complete: {processing_info['original_size_bytes']} -> "
                           f"{processing_info['final_size_bytes']} bytes, "
                           f"{processing_info['original_dimensions']} -> {processing_info['final_dimensions']}")
                
                return optimized_data, processing_info
                
        except Exception as e:
            processing_info['error'] = str(e)
            logger.error(f"Error optimizing image: {e}")
            return image_data, processing_info
    
    def _optimize_file_size(self, img: Image.Image, target_format: str, processing_info: Dict) -> bytes:
        """
        Optimize image file size through quality adjustment and format-specific options.
        
        Args:
            img: PIL Image object
            target_format: Target format ('JPEG' or 'PNG')
            processing_info: Dictionary to record optimization steps
            
        Returns:
            Optimized image bytes
        """
        if target_format == 'JPEG':
            return self._optimize_jpeg(img, processing_info)
        elif target_format == 'PNG':
            return self._optimize_png(img, processing_info)
        else:
            # Fallback to basic save
            buffer = io.BytesIO()
            img.save(buffer, format=target_format)
            return buffer.getvalue()
    
    def _optimize_jpeg(self, img: Image.Image, processing_info: Dict) -> bytes:
        """
        Optimize JPEG image through quality adjustment.
        
        Args:
            img: PIL Image object
            processing_info: Dictionary to record optimization steps
            
        Returns:
            Optimized JPEG bytes
        """
        # Start with high quality and reduce if needed
        quality_levels = [95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40]
        
        for quality in quality_levels:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            data = buffer.getvalue()
            
            processing_info['quality_adjustments'].append(f"JPEG quality {quality}: {len(data)} bytes")
            
            if len(data) <= self.MAX_FILE_SIZE:
                processing_info['quality_adjustments'].append(f"Final JPEG quality: {quality}")
                return data
        
        # If still too large, use lowest quality
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=30, optimize=True)
        data = buffer.getvalue()
        processing_info['quality_adjustments'].append(f"Final JPEG quality: 30 (forced)")
        return data
    
    def _optimize_png(self, img: Image.Image, processing_info: Dict) -> bytes:
        """
        Optimize PNG image through various compression options.
        
        Args:
            img: PIL Image object
            processing_info: Dictionary to record optimization steps
            
        Returns:
            Optimized PNG bytes
        """
        # Try different PNG optimization strategies
        strategies = [
            {'optimize': True, 'compress_level': 9},
            {'optimize': True, 'compress_level': 6},
            {'optimize': False, 'compress_level': 9},
        ]
        
        best_data = None
        best_size = float('inf')
        
        for i, params in enumerate(strategies):
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', **params)
            data = buffer.getvalue()
            
            processing_info['quality_adjustments'].append(
                f"PNG strategy {i+1} (compress_level={params['compress_level']}, "
                f"optimize={params['optimize']}): {len(data)} bytes"
            )
            
            if len(data) < best_size:
                best_data = data
                best_size = len(data)
            
            if len(data) <= self.MAX_FILE_SIZE:
                processing_info['quality_adjustments'].append(f"PNG optimization successful")
                return data
        
        # If PNG is still too large, consider converting to JPEG
        if best_size > self.MAX_FILE_SIZE:
            processing_info['quality_adjustments'].append("PNG too large, converting to JPEG")
            # Convert to RGB and try JPEG optimization
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            
            return self._optimize_jpeg(img, processing_info)
        
        processing_info['quality_adjustments'].append(f"Best PNG compression used")
        return best_data
    
    def process_artwork(self, image_data: bytes, force_compliance: bool = True) -> Dict[str, Union[bytes, bool, List, Dict]]:
        """
        Complete artwork processing pipeline: validate, resize, and optimize.
        
        Args:
            image_data: Raw image bytes
            force_compliance: If True, always try to make artwork compliant
            
        Returns:
            Dictionary with processing results:
            {
                'is_compliant': bool,
                'processed_data': bytes or None,
                'original_info': dict,
                'processing_info': dict,
                'validation_issues': list,
                'needs_processing': bool
            }
        """
        result = {
            'is_compliant': False,
            'processed_data': None,
            'original_info': {},
            'processing_info': {},
            'validation_issues': [],
            'needs_processing': False
        }
        
        try:
            # Get original image info
            result['original_info'] = self.get_image_info(image_data)
            
            # Validate original artwork
            is_valid, issues = self.validate_artwork(image_data)
            result['validation_issues'] = issues
            result['needs_processing'] = not is_valid
            
            if is_valid:
                # Already compliant, no processing needed
                result['is_compliant'] = True
                result['processed_data'] = image_data
                logger.info("Artwork already meets Traktor 3 specifications")
            elif force_compliance:
                # Process artwork to make it compliant
                processed_data, processing_info = self.resize_and_optimize(image_data)
                result['processing_info'] = processing_info
                
                # Validate processed artwork
                is_processed_valid, processed_issues = self.validate_artwork(processed_data)
                result['is_compliant'] = is_processed_valid
                
                if is_processed_valid:
                    result['processed_data'] = processed_data
                    logger.info("Artwork successfully processed to meet Traktor 3 specifications")
                else:
                    logger.warning(f"Processed artwork still doesn't meet specifications: {processed_issues}")
            else:
                logger.info("Artwork doesn't meet specifications and force_compliance is False")
                
        except Exception as e:
            logger.error(f"Error in artwork processing pipeline: {e}")
            result['processing_info']['error'] = str(e)
        
        return result 