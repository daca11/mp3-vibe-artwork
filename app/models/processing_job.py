"""
Processing job management for MP3 Artwork Manager
Handles individual file processing tasks and status tracking
"""
import uuid
import os
from datetime import datetime, timezone
from enum import Enum
from flask import current_app


class ProcessingStep(Enum):
    """Processing step enumeration"""
    INITIALIZING = "initializing"
    EXTRACTING_METADATA = "extracting_metadata"
    EXTRACTING_ARTWORK = "extracting_artwork"
    SEARCHING_MUSICBRAINZ = "searching_musicbrainz"
    OPTIMIZING_ARTWORK = "optimizing_artwork"
    WAITING_USER_SELECTION = "waiting_user_selection"
    EMBEDDING_ARTWORK = "embedding_artwork"
    GENERATING_OUTPUT = "generating_output"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJob:
    """Represents a processing job for a single file"""
    
    def __init__(self, file_id):
        self.job_id = str(uuid.uuid4())
        self.file_id = file_id
        self.current_step = ProcessingStep.INITIALIZING
        self.progress_percent = 0
        self.started_at = datetime.now(timezone.utc)
        self.completed_at = None
        self.error_message = None
        self.steps_completed = []
        self.metadata = {}
        self.embedded_artwork = []
        self.musicbrainz_artwork = []
        
        # Step weights for progress calculation
        self.step_weights = {
            ProcessingStep.INITIALIZING: 5,
            ProcessingStep.EXTRACTING_METADATA: 15,
            ProcessingStep.EXTRACTING_ARTWORK: 20,
            ProcessingStep.SEARCHING_MUSICBRAINZ: 25,
            ProcessingStep.OPTIMIZING_ARTWORK: 15,
            ProcessingStep.WAITING_USER_SELECTION: 0,  # User interaction, no progress
            ProcessingStep.EMBEDDING_ARTWORK: 10,
            ProcessingStep.GENERATING_OUTPUT: 10,
            ProcessingStep.COMPLETED: 0,
            ProcessingStep.FAILED: 0
        }
    
    def update_step(self, step, error_message=None):
        """Update current processing step"""
        self.current_step = step
        
        if error_message:
            self.error_message = error_message
            self.current_step = ProcessingStep.FAILED
        
        if step == ProcessingStep.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)
            self.progress_percent = 100
        elif step == ProcessingStep.FAILED:
            self.completed_at = datetime.now(timezone.utc)
        else:
            # Add current step to completed steps for progress calculation
            if step not in self.steps_completed and step not in [ProcessingStep.WAITING_USER_SELECTION, ProcessingStep.COMPLETED, ProcessingStep.FAILED]:
                self.steps_completed.append(step)
            
            # Calculate progress based on completed steps
            completed_weight = sum(
                self.step_weights.get(s, 0) for s in self.steps_completed
            )
            total_weight = sum(
                weight for step, weight in self.step_weights.items()
                if step not in [ProcessingStep.WAITING_USER_SELECTION, ProcessingStep.COMPLETED, ProcessingStep.FAILED]
            )
            
            if total_weight > 0:
                self.progress_percent = min(95, int((completed_weight / total_weight) * 100))
    
    def process_file(self):
        """
        Main processing function for a file
        Handles the complete workflow from metadata extraction to ready for user selection
        """
        from app.models.file_queue import get_queue, FileStatus
        from app.services.mp3_processor import MP3Processor, MP3ProcessingError
        
        queue = get_queue()
        file_obj = queue.get_file(self.file_id)
        
        if not file_obj:
            raise Exception(f"File not found: {self.file_id}")
        
        processor = MP3Processor()
        
        try:
            # Update queue status
            queue.update_file(self.file_id, status='processing', progress=0)
            
            # Step 1: Initialize
            self.update_step(ProcessingStep.INITIALIZING)
            current_app.logger.info(f"Starting processing for {file_obj.filename}")
            
            # Validate file exists
            if not os.path.exists(file_obj.file_path):
                raise MP3ProcessingError(f"File not found: {file_obj.file_path}")
            
            # Step 2: Extract metadata
            self.update_step(ProcessingStep.EXTRACTING_METADATA)
            queue.update_file(self.file_id, progress=self.progress_percent)
            
            self.metadata = processor.extract_metadata(file_obj.file_path)
            file_obj.metadata = self.metadata
            
            # Step 3: Extract embedded artwork
            self.update_step(ProcessingStep.EXTRACTING_ARTWORK)
            queue.update_file(self.file_id, progress=self.progress_percent)
            
            self.embedded_artwork = processor.extract_embedded_artwork(file_obj.file_path)
            
            # Add embedded artwork to queue file
            for artwork in self.embedded_artwork:
                file_obj.add_artwork_option(
                    source='embedded',
                    image_path=artwork['image_path'],
                    dimensions=artwork['dimensions'],
                    file_size=artwork['file_size'],
                    metadata={
                        'format': artwork['format'],
                        'mime_type': artwork['mime_type'],
                        'picture_type': artwork['picture_type'],
                        'description': artwork['description']
                    }
                )
            
            # Step 4: Get search terms for MusicBrainz
            self.update_step(ProcessingStep.SEARCHING_MUSICBRAINZ)
            queue.update_file(self.file_id, progress=self.progress_percent)
            
            search_terms = processor.get_search_terms(file_obj.file_path, file_obj.filename)
            current_app.logger.info(f"Search terms for {file_obj.filename}: {search_terms}")
            
            # Search MusicBrainz for additional artwork
            try:
                from app.services.musicbrainz_service import MusicBrainzService, MusicBrainzError
                mb_service = MusicBrainzService()
                
                current_app.logger.info(f"Searching MusicBrainz for artwork: {search_terms}")
                musicbrainz_artwork = mb_service.search_and_get_artwork(
                    artist=search_terms.get('artist'),
                    title=search_terms.get('title'),
                    album=search_terms.get('album'),
                    max_results=3  # Limit to avoid too many requests
                )
                
                # Add MusicBrainz artwork to the file object
                if musicbrainz_artwork:
                    for artwork_info in musicbrainz_artwork:
                        file_obj.add_artwork_option(
                            source='musicbrainz',
                            image_path=artwork_info.get('image_url'), # Use URL directly
                            dimensions=None,  # Will be determined later if needed
                            file_size=None, # Cannot determine file size from URL directly
                            metadata={
                                'release_id': artwork_info.get('release_id'),
                                'release_title': artwork_info.get('release_title'),
                                'release_artist': artwork_info.get('release_artist'),
                                'release_date': artwork_info.get('release_date'),
                                'primary_type': artwork_info.get('primary_type'),
                                'is_front': artwork_info.get('is_front'),
                                'source_url': artwork_info.get('image_url')
                            }
                        )
                    
                    self.musicbrainz_artwork = musicbrainz_artwork
                    current_app.logger.info(f"MusicBrainz search completed: found {len(self.musicbrainz_artwork)} artwork options")
                
            except MusicBrainzError as e:
                current_app.logger.error(f"MusicBrainz search failed: {e}")
                self.musicbrainz_artwork = []
            except Exception as e:
                current_app.logger.error(f"Unexpected error during MusicBrainz search: {e}")
                self.musicbrainz_artwork = []
            
            # Step 5: Optimize artwork
            self.update_step(ProcessingStep.OPTIMIZING_ARTWORK)
            queue.update_file(self.file_id, progress=self.progress_percent)
            
            # Optimize embedded artwork if needed
            from app.services.image_optimizer import ImageOptimizer, ImageOptimizationError
            optimizer = ImageOptimizer()
            
            optimized_artwork = []
            for artwork in self.embedded_artwork:
                try:
                    if artwork.get('needs_optimization', False):
                        current_app.logger.info(f"Optimizing embedded artwork: {artwork['image_path']}")
                        optimization_result = optimizer.optimize_image(
                            artwork['image_path'],
                            target_format='JPEG',
                            quality=90
                        )
                        
                        # Update artwork info with optimized version
                        artwork.update({
                            'optimized_path': optimization_result['output_path'],
                            'optimized_dimensions': optimization_result['final_dimensions'],
                            'optimized_size': optimization_result['final_size'],
                            'optimization_result': optimization_result
                        })
                        
                        current_app.logger.info(f"Artwork optimized: {optimization_result['size_reduction']} bytes saved")
                    else:
                        current_app.logger.info(f"Artwork already meets requirements: {artwork['image_path']}")
                        
                    optimized_artwork.append(artwork)
                    
                except ImageOptimizationError as e:
                    current_app.logger.error(f"Failed to optimize artwork: {e}")
                    # Keep original artwork even if optimization fails
                    optimized_artwork.append(artwork)
            
            self.embedded_artwork = optimized_artwork
            
            # Update final status - ready for user selection
            self.update_step(ProcessingStep.WAITING_USER_SELECTION)
            queue.update_file(
                self.file_id, 
                status='completed',  # For now, mark as completed since we have no user selection yet
                progress=100,
                metadata=self.metadata
            )
            
            current_app.logger.info(f"Processing completed for {file_obj.filename}")
            return True
            
        except Exception as e:
            from app.services.mp3_processor import MP3ProcessingError
            error_msg = f"Processing failed for {file_obj.filename}: {str(e)}"
            self.update_step(ProcessingStep.FAILED, error_msg)
            queue.update_file(
                self.file_id,
                status='error',
                error_message=error_msg,
                progress=0
            )
            current_app.logger.error(error_msg)
            raise MP3ProcessingError(error_msg)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'job_id': self.job_id,
            'file_id': self.file_id,
            'current_step': self.current_step.value,
            'progress_percent': self.progress_percent,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'steps_completed': [step.value for step in self.steps_completed],
            'metadata': self.metadata,
            'embedded_artwork_count': len(self.embedded_artwork),
            'musicbrainz_artwork_count': len(self.musicbrainz_artwork)
        }


def create_processing_job(file_id):
    """Create and start a processing job for a file"""
    job = ProcessingJob(file_id)
    
    try:
        job.process_file()
        return job
    except Exception as e:
        current_app.logger.error(f"Failed to create processing job for {file_id}: {str(e)}")
        raise


def process_file_async(file_id):
    """
    Process a file asynchronously
    For now, this is synchronous but in Phase 8 we'll make it truly async
    """
    try:
        job = create_processing_job(file_id)
        return job.to_dict()
    except Exception as e:
        current_app.logger.error(f"Async processing failed for {file_id}: {str(e)}")
        raise


def batch_process_files(file_ids):
    """
    Process multiple files
    For now, processes sequentially but in Phase 8 we'll add concurrency
    """
    results = []
    
    for file_id in file_ids:
        try:
            job_result = process_file_async(file_id)
            results.append(job_result)
        except Exception as e:
            current_app.logger.error(f"Batch processing failed for {file_id}: {str(e)}")
            results.append({
                'file_id': file_id,
                'error': str(e),
                'success': False
            })
    
    return results
