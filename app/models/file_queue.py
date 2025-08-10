"""
File queue management for MP3 Artwork Manager
"""
import uuid
import json
import os
from datetime import datetime, timezone
from enum import Enum
from flask import current_app


class FileStatus(Enum):
    """File processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class QueuedFile:
    """Represents a file in the processing queue"""
    
    def __init__(self, filename, file_path, size, mime_type=None):
        self.id = str(uuid.uuid4())
        self.filename = filename
        self.file_path = file_path
        self.size = size
        self.mime_type = mime_type
        self.status = FileStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.progress = 0
        self.error_message = None
        self.metadata = {}
        self.artwork_options = []
        self.selected_artwork = None
        self.output_path = None
    
    def update_status(self, status, error_message=None, progress=None):
        """Update file status"""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        
        if error_message:
            self.error_message = error_message
        
        if progress is not None:
            self.progress = progress
    
    def add_artwork_option(self, source, image_path, dimensions=None, file_size=None, metadata=None):
        """Add an artwork option"""
        artwork = {
            'id': str(uuid.uuid4()),
            'source': source,  # 'embedded', 'musicbrainz', etc.
            'image_path': image_path,
            'dimensions': dimensions,
            'file_size': file_size,
            'metadata': metadata or {}
        }
        self.artwork_options.append(artwork)
        return artwork['id']
    
    def select_artwork(self, artwork_id):
        """Select an artwork option"""
        for artwork in self.artwork_options:
            if artwork['id'] == artwork_id:
                self.selected_artwork = artwork
                return True
        return False
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_path': self.file_path,
            'size': self.size,
            'mime_type': self.mime_type,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'progress': self.progress,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'artwork_options': self.artwork_options,
            'selected_artwork': self.selected_artwork,
            'output_path': self.output_path
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary"""
        file_obj = cls(
            filename=data['filename'],
            file_path=data['file_path'],
            size=data['size'],
            mime_type=data.get('mime_type')
        )
        
        file_obj.id = data['id']
        file_obj.status = FileStatus(data['status'])
        file_obj.created_at = datetime.fromisoformat(data['created_at'])
        file_obj.updated_at = datetime.fromisoformat(data['updated_at'])
        file_obj.progress = data.get('progress', 0)
        file_obj.error_message = data.get('error_message')
        file_obj.metadata = data.get('metadata', {})
        file_obj.artwork_options = data.get('artwork_options', [])
        file_obj.selected_artwork = data.get('selected_artwork')
        file_obj.output_path = data.get('output_path')
        
        return file_obj


class FileQueue:
    """File queue manager using JSON file storage"""
    
    def __init__(self, queue_file='queue.json'):
        self.queue_file = queue_file
        self._queue = {}
        self._load_queue()
    
    def _get_queue_path(self):
        """Get the full path to the queue file"""
        return os.path.join(current_app.config['TEMP_FOLDER'], self.queue_file)
    
    def _load_queue(self):
        """Load queue from JSON file"""
        try:
            queue_path = self._get_queue_path()
            if os.path.exists(queue_path):
                with open(queue_path, 'r') as f:
                    data = json.load(f)
                    self._queue = {
                        file_id: QueuedFile.from_dict(file_data)
                        for file_id, file_data in data.items()
                    }
        except Exception as e:
            current_app.logger.error(f"Failed to load queue: {e}")
            self._queue = {}
    
    def _save_queue(self):
        """Save queue to JSON file"""
        try:
            queue_path = self._get_queue_path()
            os.makedirs(os.path.dirname(queue_path), exist_ok=True)
            
            data = {
                file_id: file_obj.to_dict()
                for file_id, file_obj in self._queue.items()
            }
            
            with open(queue_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            current_app.logger.error(f"Failed to save queue: {e}")
    
    def add_file(self, filename, file_path, size, mime_type=None):
        """Add a file to the queue"""
        queued_file = QueuedFile(filename, file_path, size, mime_type)
        self._queue[queued_file.id] = queued_file
        self._save_queue()
        return queued_file
    
    def get_file(self, file_id):
        """Get a file from the queue"""
        return self._queue.get(file_id)
    
    def remove_file(self, file_id):
        """Remove a file from the queue"""
        if file_id in self._queue:
            file_obj = self._queue[file_id]
            
            # Clean up file if it exists
            if file_obj.file_path and os.path.exists(file_obj.file_path):
                try:
                    os.remove(file_obj.file_path)
                except Exception as e:
                    current_app.logger.error(f"Failed to remove file {file_obj.file_path}: {e}")
            
            # Clean up output file if it exists
            if file_obj.output_path and os.path.exists(file_obj.output_path):
                try:
                    os.remove(file_obj.output_path)
                except Exception as e:
                    current_app.logger.error(f"Failed to remove output file {file_obj.output_path}: {e}")
            
            # Clean up artwork files
            if file_obj.artwork_options:
                for artwork in file_obj.artwork_options:
                    if artwork.get('image_path') and os.path.exists(artwork['image_path']):
                        try:
                            os.remove(artwork['image_path'])
                        except Exception as e:
                            current_app.logger.error(f"Failed to remove artwork file {artwork['image_path']}: {e}")
                    if artwork.get('optimized_path') and os.path.exists(artwork['optimized_path']):
                        try:
                            os.remove(artwork['optimized_path'])
                        except Exception as e:
                            current_app.logger.error(f"Failed to remove optimized artwork file {artwork['optimized_path']}: {e}")
            
            del self._queue[file_id]
            self._save_queue()
            return True
        return False
    
    def get_all_files(self):
        """Get all files in the queue"""
        return list(self._queue.values())
    
    def get_files_by_status(self, status):
        """Get files by status"""
        return [f for f in self._queue.values() if f.status == status]

    def clear(self):
        """Clear the entire queue"""
        # Get all file IDs before clearing
        file_ids = list(self._queue.keys())
        
        # Remove each file individually to trigger cleanup
        for file_id in file_ids:
            self.remove_file(file_id)
        
        # Ensure the queue is empty
        self._queue.clear()
        self._save_queue()
    
    def update_file(self, file_id, **kwargs):
        """Update file properties"""
        if file_id in self._queue:
            file_obj = self._queue[file_id]
            
            if 'status' in kwargs:
                file_obj.update_status(
                    FileStatus(kwargs['status']),
                    kwargs.get('error_message'),
                    kwargs.get('progress')
                )
            
            for key, value in kwargs.items():
                if hasattr(file_obj, key) and key not in ['status', 'error_message', 'progress']:
                    setattr(file_obj, key, value)
            
            self._save_queue()
            return file_obj
        return None


# Global queue instance
_queue_instance = None


def get_queue():
    """Get the global queue instance"""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = FileQueue()
    return _queue_instance
