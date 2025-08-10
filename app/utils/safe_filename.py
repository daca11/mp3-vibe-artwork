import re
import os

def safe_filename(filename):
    """
    Sanitizes a filename by removing or replacing characters that are invalid
    in common filesystems, while trying to preserve the original name as much as possible.
    """
    # Replace slashes and backslashes with underscores
    filename = re.sub(r'[/\\]', '_', filename)
    
    # Remove characters that are problematic in Windows and/or Linux/macOS
    # This includes: < > : " | ? * and control characters (0x00-0x1F)
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
    
    # Avoid names that are reserved in Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    name, _, ext = filename.rpartition('.')
    if name.upper() in reserved_names:
        filename = f"_{filename}"
        
    # Filename should not start or end with a space or a period
    filename = filename.strip(' .')
    
    # Limit filename length (e.g., to 255 bytes, common limit)
    # This is a simplification; proper handling is more complex.
    max_len = 250  # A bit less than 255 to be safe
    if len(filename.encode('utf-8')) > max_len:
        # Simple truncation, could be smarter
        name, ext = os.path.splitext(filename)
        # Truncate the name part
        while len((name + ext).encode('utf-8')) > max_len:
            name = name[:-1]
        filename = name + ext
        
    if not filename:
        return "_empty_filename_"

    return filename
