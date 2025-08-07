"""
Bulk Operations Service for MP3 Artwork Manager
Handles bulk file processing and operations
"""
from flask import current_app
from app.models.file_queue import get_queue
from app.services.task_manager import get_task_manager
from app.services.mp3_output_service import MP3OutputService
from app.services.musicbrainz_service import MusicBrainzService
from app.models.processing_job import ProcessingJob
import time


class BulkOperationsService:
    """Service for handling bulk operations on multiple files"""
    
    def __init__(self):
        self.task_manager = get_task_manager()
        self.output_service = MP3OutputService()
    
    def bulk_process_files(self, file_ids, progress_callback=None):
        """
        Process multiple files through the complete workflow
        """
        try:
            if progress_callback:
                progress_callback(0, "Initializing bulk processing")
            
            queue = get_queue()
            total_files = len(file_ids)
            processed_files = 0
            results = []
            
            current_app.logger.info(f"Starting bulk processing for {total_files} files")
            
            for i, file_id in enumerate(file_ids):
                try:
                    if progress_callback:
                        progress = int((i / total_files) * 100)
                        progress_callback(progress, f"Processing file {i+1} of {total_files}")
                    
                    file_obj = queue.get_file(file_id)
                    if not file_obj:
                        results.append({
                            'file_id': file_id,
                            'success': False,
                            'error': 'File not found'
                        })
                        continue
                    
                    # Process the file
                    processing_job = ProcessingJob(file_id)
                    processing_job.process_file()
                    
                    results.append({
                        'file_id': file_id,
                        'filename': file_obj.filename,
                        'success': True,
                        'steps_completed': len(processing_job.steps_completed),
                        'artwork_options': len(file_obj.artwork_options)
                    })
                    
                    processed_files += 1
                    
                except Exception as e:
                    current_app.logger.error(f"Failed to process file {file_id}: {str(e)}")
                    results.append({
                        'file_id': file_id,
                        'success': False,
                        'error': str(e)
                    })
            
            if progress_callback:
                progress_callback(100, "Bulk processing completed")
            
            current_app.logger.info(f"Bulk processing completed: {processed_files}/{total_files} successful")
            
            return {
                'total_files': total_files,
                'processed_files': processed_files,
                'results': results
            }
            
        except Exception as e:
            error_msg = f"Bulk processing failed: {str(e)}"
            current_app.logger.error(error_msg)
            raise Exception(error_msg)
    
    def bulk_apply_artwork_selection(self, selections, progress_callback=None):
        """
        Apply artwork selection to multiple files
        
        Args:
            selections: List of {'file_id': str, 'artwork_id': str} or {'file_id': str, 'strategy': str}
        """
        try:
            if progress_callback:
                progress_callback(0, "Applying artwork selections")
            
            queue = get_queue()
            total_selections = len(selections)
            successful = 0
            results = []
            
            for i, selection in enumerate(selections):
                try:
                    if progress_callback:
                        progress = int((i / total_selections) * 100)
                        progress_callback(progress, f"Applying selection {i+1} of {total_selections}")
                    
                    file_id = selection['file_id']
                    file_obj = queue.get_file(file_id)
                    
                    if not file_obj:
                        results.append({
                            'file_id': file_id,
                            'success': False,
                            'error': 'File not found'
                        })
                        continue
                    
                    # Apply selection based on strategy or explicit artwork_id
                    if 'artwork_id' in selection:
                        # Explicit artwork selection
                        if file_obj.select_artwork(selection['artwork_id']):
                            successful += 1
                            results.append({
                                'file_id': file_id,
                                'success': True,
                                'selected_artwork_id': selection['artwork_id']
                            })
                        else:
                            results.append({
                                'file_id': file_id,
                                'success': False,
                                'error': 'Artwork not found'
                            })
                    elif 'strategy' in selection:
                        # Strategy-based selection
                        selected_id = self._apply_selection_strategy(file_obj, selection['strategy'])
                        if selected_id:
                            file_obj.select_artwork(selected_id)
                            successful += 1
                            results.append({
                                'file_id': file_id,
                                'success': True,
                                'selected_artwork_id': selected_id,
                                'strategy_used': selection['strategy']
                            })
                        else:
                            results.append({
                                'file_id': file_id,
                                'success': False,
                                'error': 'No artwork found for strategy'
                            })
                    
                except Exception as e:
                    current_app.logger.error(f"Failed to apply selection for {file_id}: {str(e)}")
                    results.append({
                        'file_id': file_id,
                        'success': False,
                        'error': str(e)
                    })
            
            # Save queue with all selections
            queue._save_queue()
            
            if progress_callback:
                progress_callback(100, "Artwork selections applied")
            
            return {
                'total_selections': total_selections,
                'successful': successful,
                'results': results
            }
            
        except Exception as e:
            error_msg = f"Bulk artwork selection failed: {str(e)}"
            current_app.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _apply_selection_strategy(self, file_obj, strategy):
        """Apply artwork selection strategy"""
        if not file_obj.artwork_options:
            return None
        
        if strategy == 'prefer_embedded':
            # Prefer embedded artwork
            for artwork in file_obj.artwork_options:
                if artwork['source'] == 'embedded':
                    return artwork['id']
            # Fall back to first available
            return file_obj.artwork_options[0]['id']
        
        elif strategy == 'prefer_musicbrainz':
            # Prefer MusicBrainz artwork
            for artwork in file_obj.artwork_options:
                if artwork['source'] == 'musicbrainz':
                    return artwork['id']
            # Fall back to first available
            return file_obj.artwork_options[0]['id']
        
        elif strategy == 'highest_resolution':
            # Select highest resolution artwork
            best_artwork = max(
                file_obj.artwork_options,
                key=lambda a: a.get('dimensions', {}).get('width', 0) * a.get('dimensions', {}).get('height', 0)
            )
            return best_artwork['id']
        
        elif strategy == 'smallest_file':
            # Select smallest file size
            best_artwork = min(
                file_obj.artwork_options,
                key=lambda a: a.get('file_size', float('inf'))
            )
            return best_artwork['id']
        
        else:
            # Default: first available
            return file_obj.artwork_options[0]['id']
    
    def bulk_generate_output(self, file_ids, create_zip=True, progress_callback=None):
        """
        Generate output files for multiple files
        """
        try:
            if progress_callback:
                progress_callback(0, "Generating output files")
            
            queue = get_queue()
            total_files = len(file_ids)
            successful = 0
            output_files = []
            results = []
            
            for i, file_id in enumerate(file_ids):
                try:
                    if progress_callback:
                        progress = int((i / total_files) * 85)  # Reserve 15% for ZIP creation
                        progress_callback(progress, f"Generating output {i+1} of {total_files}")
                    
                    file_obj = queue.get_file(file_id)
                    if not file_obj:
                        results.append({
                            'file_id': file_id,
                            'success': False,
                            'error': 'File not found'
                        })
                        continue
                    
                    if not file_obj.selected_artwork:
                        results.append({
                            'file_id': file_id,
                            'success': False,
                            'error': 'No artwork selected'
                        })
                        continue
                    
                    # Generate output
                    result = self.output_service.process_file_with_selection(file_obj)
                    
                    # Update file object
                    file_obj.output_path = result['output_path']
                    file_obj.output_size = result['output_size']
                    file_obj.status = 'completed'
                    
                    output_files.append(result['output_path'])
                    successful += 1
                    
                    results.append({
                        'file_id': file_id,
                        'success': True,
                        'output_filename': result['output_filename'],
                        'output_size': result['output_size']
                    })
                    
                except Exception as e:
                    current_app.logger.error(f"Failed to generate output for {file_id}: {str(e)}")
                    results.append({
                        'file_id': file_id,
                        'success': False,
                        'error': str(e)
                    })
            
            # Save queue
            queue._save_queue()
            
            # Create ZIP if requested and we have output files
            archive_info = None
            if create_zip and output_files:
                if progress_callback:
                    progress_callback(90, "Creating ZIP archive")
                
                try:
                    archive_info = self.output_service.create_zip_archive(output_files)
                except Exception as e:
                    current_app.logger.error(f"Failed to create ZIP archive: {str(e)}")
            
            if progress_callback:
                progress_callback(100, "Bulk output generation completed")
            
            return {
                'total_files': total_files,
                'successful': successful,
                'results': results,
                'archive': archive_info
            }
            
        except Exception as e:
            error_msg = f"Bulk output generation failed: {str(e)}"
            current_app.logger.error(error_msg)
            raise Exception(error_msg)
    
    def start_bulk_processing_task(self, file_ids):
        """Start bulk processing as a background task"""
        task_id = self.task_manager.create_task(
            name=f"Bulk Processing ({len(file_ids)} files)",
            target_func=self.bulk_process_files,
            args=(file_ids,)
        )
        
        if self.task_manager.start_task(task_id):
            current_app.logger.info(f"Started bulk processing task {task_id}")
            return task_id
        else:
            current_app.logger.error(f"Failed to start bulk processing task {task_id}")
            return None
    
    def start_bulk_output_task(self, file_ids, create_zip=True):
        """Start bulk output generation as a background task"""
        task_id = self.task_manager.create_task(
            name=f"Bulk Output Generation ({len(file_ids)} files)",
            target_func=self.bulk_generate_output,
            args=(file_ids, create_zip)
        )
        
        if self.task_manager.start_task(task_id):
            current_app.logger.info(f"Started bulk output task {task_id}")
            return task_id
        else:
            current_app.logger.error(f"Failed to start bulk output task {task_id}")
            return None
