"""
File validation utilities for MP3 Artwork Manager
"""
import os
from werkzeug.utils import secure_filename
from flask import current_app

# Try to import magic, but make it optional
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


def safe_filename(filename):
    """
    Custom filename safety function that preserves original filenames exactly.
    Unlike werkzeug's secure_filename, this preserves the original name
    while ensuring it's safe for filesystem operations.
    
    This is critical per user requirements - original MP3 filenames must be preserved exactly.
    """
    # Only remove characters that are truly problematic for filesystems
    # Remove null bytes and control characters
    cleaned = ''.join(c for c in filename if ord(c) >= 32)
    
    # Ensure the filename isn't empty
    if not cleaned:
        return 'unnamed_file.mp3'
    
    # Ensure it has an extension
    if not cleaned.lower().endswith('.mp3'):
        cleaned += '.mp3'
    
    return cleaned


def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return filename.lower().endswith('.mp3')


def validate_file_size(file):
    """Check if file size is within limits"""
    max_size = current_app.config['MAX_CONTENT_LENGTH']
    
    # Get file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)  # Reset file pointer
    
    return size <= max_size


def validate_mp3_file(file):
    """
    Comprehensive MP3 file validation
    Returns (is_valid, error_message)
    """
    if not file:
        return False, "No file provided"
    
    if file.filename == '':
        return False, "No file selected"
    
    # Check file extension
    if not allowed_file(file.filename):
        return False, f"File '{file.filename}' is not an MP3 file"
    
    # Check file size
    if not validate_file_size(file):
        max_mb = current_app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
        return False, f"File '{file.filename}' exceeds maximum size of {max_mb:.0f}MB"
    
    # Check file type using python-magic if available
    if HAS_MAGIC:
        try:
            file_mime = magic.from_buffer(file.read(1024), mime=True)
            file.seek(0)  # Reset file pointer
            
            # Accept various MP3 MIME types
            valid_mime_types = [
                'audio/mpeg',
                'audio/mp3',
                'application/octet-stream'  # Some systems report MP3 as this
            ]
            
            if file_mime not in valid_mime_types:
                return False, f"File '{file.filename}' is not a valid MP3 file (detected: {file_mime})"
        
        except Exception as e:
            # If magic fails, we'll trust the extension check
            current_app.logger.warning(f"Magic file type detection failed for {file.filename}: {e}")
    else:
        # If magic is not available, warn but continue with extension check
        current_app.logger.info(f"python-magic not available, relying on extension check for {file.filename}")
    
    return True, None


def get_file_info(file):
    """Extract basic file information"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    return {
        'filename': file.filename,
        'safe_filename': safe_filename(file.filename),
        'size': size,
        'mime_type': file.content_type
    }
