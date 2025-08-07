"""
MP3 Output Service for MP3 Artwork Manager
Handles embedding artwork into MP3 files and generating output files
"""
import os
import shutil
import tempfile
from flask import current_app
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from PIL import Image
import mimetypes


class MP3OutputError(Exception):
    """Custom exception for MP3 output service errors"""
    pass


class MP3OutputService:
    """Service for creating output MP3 files with embedded artwork"""
    
    def __init__(self):
        pass
    
    def embed_artwork(self, mp3_file_path, artwork_path, output_path=None, preserve_metadata=True):
        """
        Embed artwork into MP3 file
        
        Args:
            mp3_file_path: Path to source MP3 file
            artwork_path: Path to artwork image file
            output_path: Path for output file (optional, creates temp file if None)
            preserve_metadata: Whether to preserve existing ID3 tags
            
        Returns:
            dict with success status, output path, and metadata
        """
        try:
            if not os.path.exists(mp3_file_path):
                raise MP3OutputError(f"MP3 file not found: {mp3_file_path}")
            
            if not os.path.exists(artwork_path):
                raise MP3OutputError(f"Artwork file not found: {artwork_path}")
            
            # Generate output path if not provided
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix='_with_artwork.mp3',
                    dir=current_app.config['OUTPUT_FOLDER']
                )
                output_path = temp_file.name
                temp_file.close()
            
            # Copy original file to output location
            shutil.copy2(mp3_file_path, output_path)
            
            current_app.logger.info(f"Embedding artwork from {artwork_path} into {output_path}")
            
            # Load MP3 file
            audio_file = MP3(output_path, ID3=ID3)
            
            # Add ID3 tag if it doesn't exist
            try:
                audio_file.add_tags()
            except Exception:
                pass  # Tags already exist
            
            # Get image data and MIME type
            with open(artwork_path, 'rb') as img_file:
                image_data = img_file.read()
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(artwork_path)
            if not mime_type:
                # Try to determine from PIL
                try:
                    with Image.open(artwork_path) as img:
                        format_map = {
                            'JPEG': 'image/jpeg',
                            'PNG': 'image/png',
                            'GIF': 'image/gif',
                            'BMP': 'image/bmp'
                        }
                        mime_type = format_map.get(img.format, 'image/jpeg')
                except Exception:
                    mime_type = 'image/jpeg'  # Default fallback
            
            current_app.logger.info(f"Detected MIME type: {mime_type}")
            
            # Remove existing APIC frames (artwork)
            if 'APIC:' in audio_file:
                del audio_file['APIC:']
            
            # Remove all APIC frames
            apic_keys = [key for key in audio_file.keys() if key.startswith('APIC')]
            for key in apic_keys:
                del audio_file[key]
            
            # Add new artwork
            audio_file.tags.add(
                APIC(
                    encoding=3,  # UTF-8
                    mime=mime_type,
                    type=3,  # Cover (front)
                    desc='Front Cover',
                    data=image_data
                )
            )
            
            # Save the file
            audio_file.save(v2_version=3, v23_sep='/')
            
            # Get file info
            output_size = os.path.getsize(output_path)
            original_size = os.path.getsize(mp3_file_path)
            artwork_size = len(image_data)
            
            current_app.logger.info(f"Successfully embedded artwork. Output size: {output_size} bytes")
            
            return {
                'success': True,
                'output_path': output_path,
                'original_size': original_size,
                'output_size': output_size,
                'artwork_size': artwork_size,
                'size_increase': output_size - original_size,
                'mime_type': mime_type,
                'artwork_embedded': True
            }
            
        except Exception as e:
            error_msg = f"Failed to embed artwork: {str(e)}"
            current_app.logger.error(error_msg)
            
            # Clean up partial output file
            if output_path and os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except:
                    pass
            
            raise MP3OutputError(error_msg)
    
    def process_file_with_selection(self, file_obj, output_filename=None):
        """
        Process a file object with selected artwork
        
        Args:
            file_obj: FileObject instance with selected artwork
            output_filename: Custom output filename (optional)
            
        Returns:
            dict with processing results
        """
        try:
            if not file_obj.selected_artwork:
                raise MP3OutputError("No artwork selected for this file")
            
            selected_artwork = file_obj.selected_artwork
            
            # Determine artwork path (use optimized version if available)
            artwork_path = selected_artwork.get('optimized_path') or selected_artwork['image_path']
            
            if not os.path.exists(artwork_path):
                raise MP3OutputError(f"Selected artwork not found: {artwork_path}")
            
            # Generate output filename
            if output_filename is None:
                base_name = os.path.splitext(file_obj.filename)[0]
                output_filename = f"{base_name}_with_artwork.mp3"
            
            output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
            
            # Embed artwork
            result = self.embed_artwork(
                mp3_file_path=file_obj.file_path,
                artwork_path=artwork_path,
                output_path=output_path
            )
            
            # Add file-specific metadata
            result.update({
                'original_filename': file_obj.filename,
                'output_filename': output_filename,
                'selected_artwork_source': selected_artwork['source'],
                'artwork_metadata': selected_artwork.get('metadata', {})
            })
            
            current_app.logger.info(f"Successfully processed {file_obj.filename} -> {output_filename}")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process file {file_obj.filename}: {str(e)}"
            current_app.logger.error(error_msg)
            raise MP3OutputError(error_msg)
    
    def batch_process_files(self, file_objects, output_pattern=None):
        """
        Process multiple files with their selected artwork
        
        Args:
            file_objects: List of FileObject instances
            output_pattern: Pattern for output filenames (optional)
            
        Returns:
            dict with batch processing results
        """
        results = []
        successful = 0
        failed = 0
        
        for file_obj in file_objects:
            try:
                # Generate output filename using pattern if provided
                output_filename = None
                if output_pattern:
                    base_name = os.path.splitext(file_obj.filename)[0]
                    output_filename = output_pattern.replace('{filename}', base_name)
                
                result = self.process_file_with_selection(file_obj, output_filename)
                results.append({
                    'file_id': file_obj.id,
                    'success': True,
                    'result': result
                })
                successful += 1
                
            except Exception as e:
                current_app.logger.error(f"Failed to process {file_obj.filename}: {str(e)}")
                results.append({
                    'file_id': file_obj.id,
                    'success': False,
                    'error': str(e),
                    'filename': file_obj.filename
                })
                failed += 1
        
        current_app.logger.info(f"Batch processing completed: {successful} successful, {failed} failed")
        
        return {
            'total_files': len(file_objects),
            'successful': successful,
            'failed': failed,
            'results': results
        }
    
    def create_zip_archive(self, file_paths, archive_name=None):
        """
        Create a ZIP archive containing multiple output files
        
        Args:
            file_paths: List of file paths to include
            archive_name: Name for the archive (optional)
            
        Returns:
            dict with archive information
        """
        try:
            import zipfile
            
            if archive_name is None:
                archive_name = 'mp3_artwork_output.zip'
            
            archive_path = os.path.join(current_app.config['OUTPUT_FOLDER'], archive_name)
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        # Use just the filename in the archive
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
                        current_app.logger.debug(f"Added {file_path} to archive as {arcname}")
            
            archive_size = os.path.getsize(archive_path)
            
            current_app.logger.info(f"Created ZIP archive: {archive_path} ({archive_size} bytes)")
            
            return {
                'success': True,
                'archive_path': archive_path,
                'archive_name': archive_name,
                'archive_size': archive_size,
                'files_included': len(file_paths)
            }
            
        except Exception as e:
            error_msg = f"Failed to create ZIP archive: {str(e)}"
            current_app.logger.error(error_msg)
            raise MP3OutputError(error_msg)
    
    def validate_output_file(self, mp3_path):
        """
        Validate that the output MP3 file is valid and contains artwork
        
        Args:
            mp3_path: Path to MP3 file to validate
            
        Returns:
            dict with validation results
        """
        try:
            if not os.path.exists(mp3_path):
                return {'valid': False, 'error': 'File not found'}
            
            # Try to load with mutagen
            audio_file = MP3(mp3_path, ID3=ID3)
            
            if audio_file.info is None:
                return {'valid': False, 'error': 'Invalid MP3 file'}
            
            # Check for artwork
            has_artwork = False
            artwork_info = {}
            
            for key in audio_file.keys():
                if key.startswith('APIC'):
                    has_artwork = True
                    apic = audio_file[key]
                    artwork_info = {
                        'mime_type': apic.mime,
                        'type': apic.type,
                        'description': apic.desc,
                        'size': len(apic.data)
                    }
                    break
            
            return {
                'valid': True,
                'has_artwork': has_artwork,
                'artwork_info': artwork_info,
                'duration': audio_file.info.length,
                'bitrate': audio_file.info.bitrate,
                'sample_rate': audio_file.info.sample_rate,
                'file_size': os.path.getsize(mp3_path)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def cleanup_temp_files(self, file_paths):
        """
        Clean up temporary files
        
        Args:
            file_paths: List of file paths to remove
        """
        cleaned = 0
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    cleaned += 1
            except Exception as e:
                current_app.logger.warning(f"Failed to cleanup {file_path}: {str(e)}")
        
        current_app.logger.info(f"Cleaned up {cleaned} temporary files")
        return cleaned
