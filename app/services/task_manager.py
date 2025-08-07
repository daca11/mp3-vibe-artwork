"""
Task Manager for MP3 Artwork Manager
Handles background processing and task management
"""
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional
from flask import current_app
from enum import Enum


class TaskStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class Task:
    """Represents a background task"""
    
    def __init__(self, task_id: str, name: str, target_func: Callable, args: tuple = (), kwargs: dict = None):
        self.id = task_id
        self.name = name
        self.target_func = target_func
        self.args = args or ()
        self.kwargs = kwargs or {}
        
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.started_at = None
        self.completed_at = None
        
        self.progress = 0
        self.current_step = ""
        self.result = None
        self.error = None
        
        self.thread = None
    
    def to_dict(self):
        """Convert task to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'current_step': self.current_step,
            'error': self.error,
            'has_result': self.result is not None
        }


class TaskManager:
    """Manages background tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.max_concurrent_tasks = 3
        self.running_tasks = 0
        self.lock = threading.Lock()
    
    def create_task(self, name: str, target_func: Callable, args: tuple = (), kwargs: dict = None) -> str:
        """Create a new background task"""
        task_id = str(uuid.uuid4())
        task = Task(task_id, name, target_func, args, kwargs)
        
        with self.lock:
            self.tasks[task_id] = task
        
        current_app.logger.info(f"Created task {task_id}: {name}")
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """Start a task if possible"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.PENDING:
                return False
            
            if self.running_tasks >= self.max_concurrent_tasks:
                current_app.logger.info(f"Task {task_id} queued - max concurrent tasks reached")
                return False
            
            # Start the task
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            self.running_tasks += 1
            
            # Capture the current app instance for the background thread
            app_instance = current_app._get_current_object()
            
            def task_wrapper():
                # Copy the application context for the background thread
                with app_instance.app_context():
                    try:
                        current_app.logger.info(f"Starting task {task_id}: {task.name}")
                        
                        # Create a progress callback
                        def update_progress(progress: int, step: str = ""):
                            task.progress = min(100, max(0, progress))
                            task.current_step = step
                        
                        # Add progress callback to kwargs if the function supports it
                        if 'progress_callback' in task.target_func.__code__.co_varnames:
                            task.kwargs['progress_callback'] = update_progress
                        
                        # Execute the task
                        result = task.target_func(*task.args, **task.kwargs)
                        
                        # Task completed successfully
                        with self.lock:
                            task.status = TaskStatus.COMPLETED
                            task.completed_at = datetime.now(timezone.utc)
                            task.result = result
                            task.progress = 100
                            task.current_step = "Completed"
                            self.running_tasks -= 1
                        
                        current_app.logger.info(f"Task {task_id} completed successfully")
                        
                        # Try to start queued tasks
                        self._try_start_queued_tasks()
                        
                    except Exception as e:
                        # Task failed
                        with self.lock:
                            task.status = TaskStatus.FAILED
                            task.completed_at = datetime.now(timezone.utc)
                            task.error = str(e)
                            self.running_tasks -= 1
                        
                        current_app.logger.error(f"Task {task_id} failed: {str(e)}")
                        
                        # Try to start queued tasks
                        self._try_start_queued_tasks()
            
            task.thread = threading.Thread(target=task_wrapper, daemon=True)
            task.thread.start()
            
            return True
    
    def _try_start_queued_tasks(self):
        """Try to start any queued tasks"""
        with self.lock:
            pending_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
            
            for task in pending_tasks:
                if self.running_tasks < self.max_concurrent_tasks:
                    # Release lock temporarily to avoid deadlock
                    task_id = task.id
                    self.lock.release()
                    self.start_task(task_id)
                    self.lock.acquire()
                else:
                    break
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get task status as dictionary"""
        task = self.get_task(task_id)
        return task.to_dict() if task else None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task (only if pending)"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                current_app.logger.info(f"Task {task_id} cancelled")
                return True
            
            return False
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        
        with self.lock:
            tasks_to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if task.completed_at and task.completed_at.timestamp() < cutoff_time:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            current_app.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
            return len(tasks_to_remove)
    
    def get_all_tasks(self) -> list:
        """Get all tasks as dictionaries"""
        with self.lock:
            return [task.to_dict() for task in self.tasks.values()]
    
    def get_stats(self) -> dict:
        """Get task manager statistics"""
        with self.lock:
            stats = {
                'total_tasks': len(self.tasks),
                'running_tasks': self.running_tasks,
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'status_counts': {}
            }
            
            for status in TaskStatus:
                count = sum(1 for task in self.tasks.values() if task.status == status)
                stats['status_counts'][status.value] = count
            
            return stats


# Global task manager instance
_task_manager = None


def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
