#!/usr/bin/env python3
"""
Error Handler Module
Comprehensive error handling and recovery system for MP3 artwork processing.
"""

import logging
import traceback
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Minor issues, processing can continue
    MEDIUM = "medium"     # Warnings, may affect quality but not fatal
    HIGH = "high"         # Serious errors, file fails but queue continues
    CRITICAL = "critical" # Critical errors, stop entire process

class ErrorCategory(Enum):
    """Error categories for better classification"""
    FILE_VALIDATION = "file_validation"
    METADATA_EXTRACTION = "metadata_extraction"
    ARTWORK_PROCESSING = "artwork_processing"
    MUSICBRAINZ_API = "musicbrainz_api"
    NETWORK_ERROR = "network_error"
    STORAGE_ERROR = "storage_error"
    SYSTEM_ERROR = "system_error"

class ProcessingError:
    """Structured error information"""
    
    def __init__(self, 
                 category: ErrorCategory,
                 severity: ErrorSeverity,
                 message: str,
                 file_path: Optional[Path] = None,
                 details: Optional[Dict] = None,
                 exception: Optional[Exception] = None,
                 timestamp: Optional[float] = None):
        self.category = category
        self.severity = severity
        self.message = message
        self.file_path = file_path
        self.details = details or {}
        self.exception = exception
        self.timestamp = timestamp or time.time()
        self.retry_count = 0
        self.max_retries = 3
    
    def can_retry(self) -> bool:
        """Check if this error can be retried"""
        return (
            self.retry_count < self.max_retries and
            self.category in [ErrorCategory.NETWORK_ERROR, ErrorCategory.MUSICBRAINZ_API] and
            self.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]
        )
    
    def increment_retry(self):
        """Increment retry counter"""
        self.retry_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'file_path': str(self.file_path) if self.file_path else None,
            'details': self.details,
            'timestamp': self.timestamp,
            'retry_count': self.retry_count,
            'exception_type': type(self.exception).__name__ if self.exception else None
        }

class ErrorHandler:
    """Comprehensive error handling and recovery system"""
    
    def __init__(self):
        self.errors: List[ProcessingError] = []
        self.error_counts: Dict[ErrorCategory, int] = {}
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}
        self.should_stop_processing = False
        
        # Initialize error counters
        for category in ErrorCategory:
            self.error_counts[category] = 0
        
        # Register default recovery strategies
        self._register_recovery_strategies()
    
    def _register_recovery_strategies(self):
        """Register default recovery strategies for different error types"""
        self.recovery_strategies[ErrorCategory.NETWORK_ERROR] = self._handle_network_error
        self.recovery_strategies[ErrorCategory.MUSICBRAINZ_API] = self._handle_api_error
        self.recovery_strategies[ErrorCategory.FILE_VALIDATION] = self._handle_file_error
        self.recovery_strategies[ErrorCategory.ARTWORK_PROCESSING] = self._handle_artwork_error
    
    def handle_error(self, 
                    category: ErrorCategory,
                    severity: ErrorSeverity,
                    message: str,
                    file_path: Optional[Path] = None,
                    details: Optional[Dict] = None,
                    exception: Optional[Exception] = None) -> ProcessingError:
        """Handle an error with appropriate logging and recovery"""
        
        error = ProcessingError(
            category=category,
            severity=severity,
            message=message,
            file_path=file_path,
            details=details,
            exception=exception
        )
        
        # Log the error
        self._log_error(error)
        
        # Store the error
        self.errors.append(error)
        self.error_counts[category] += 1
        
        # Check if we should stop processing
        if severity == ErrorSeverity.CRITICAL:
            self.should_stop_processing = True
            logger.critical(f"Critical error encountered, stopping processing: {message}")
        
        # Attempt recovery if applicable
        if category in self.recovery_strategies:
            try:
                self.recovery_strategies[category](error)
            except Exception as recovery_exception:
                logger.error(f"Recovery strategy failed: {recovery_exception}")
        
        return error
    
    def _log_error(self, error: ProcessingError):
        """Log error with appropriate level"""
        log_msg = f"[{error.category.value}] {error.message}"
        if error.file_path:
            log_msg += f" (File: {error.file_path})"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_msg, exc_info=error.exception)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_msg, exc_info=error.exception)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def _handle_network_error(self, error: ProcessingError):
        """Handle network-related errors with retry logic"""
        if error.can_retry():
            logger.info(f"Network error, will retry ({error.retry_count + 1}/{error.max_retries})")
            error.increment_retry()
            # Add exponential backoff delay
            delay = 2 ** error.retry_count
            time.sleep(min(delay, 30))  # Cap at 30 seconds
    
    def _handle_api_error(self, error: ProcessingError):
        """Handle MusicBrainz API errors"""
        if "rate limit" in error.message.lower():
            logger.info("Rate limit hit, adding delay")
            time.sleep(5)
        elif error.can_retry():
            logger.info(f"API error, will retry ({error.retry_count + 1}/{error.max_retries})")
            error.increment_retry()
            time.sleep(2)
    
    def _handle_file_error(self, error: ProcessingError):
        """Handle file validation errors"""
        # File errors usually can't be recovered from
        logger.warning(f"File validation failed, skipping file: {error.file_path}")
    
    def _handle_artwork_error(self, error: ProcessingError):
        """Handle artwork processing errors"""
        if "format" in error.message.lower() and error.can_retry():
            logger.info("Artwork format error, trying alternative processing")
            error.increment_retry()
    
    def retry_failed_operations(self, operations: List[Callable]) -> List[Any]:
        """Retry failed operations that are eligible for retry"""
        results = []
        
        for operation in operations:
            retryable_errors = [e for e in self.errors if e.can_retry()]
            
            for error in retryable_errors:
                try:
                    logger.info(f"Retrying operation for: {error.file_path}")
                    result = operation()
                    results.append(result)
                    
                    # Remove error from retry list if successful
                    if error in self.errors:
                        self.errors.remove(error)
                    
                except Exception as e:
                    error.increment_retry()
                    if not error.can_retry():
                        logger.error(f"Max retries exceeded for: {error.file_path}")
        
        return results
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a comprehensive error summary"""
        total_errors = len(self.errors)
        
        severity_counts = {}
        for severity in ErrorSeverity:
            severity_counts[severity.value] = len([e for e in self.errors if e.severity == severity])
        
        recent_errors = sorted(self.errors, key=lambda x: x.timestamp, reverse=True)[:10]
        
        return {
            'total_errors': total_errors,
            'error_counts_by_category': {cat.value: count for cat, count in self.error_counts.items()},
            'error_counts_by_severity': severity_counts,
            'should_stop_processing': self.should_stop_processing,
            'recent_errors': [error.to_dict() for error in recent_errors],
            'retryable_errors': len([e for e in self.errors if e.can_retry()])
        }
    
    def get_user_friendly_message(self, error: ProcessingError) -> str:
        """Get user-friendly error message"""
        category_messages = {
            ErrorCategory.FILE_VALIDATION: "This file appears to be corrupted or not a valid MP3",
            ErrorCategory.METADATA_EXTRACTION: "Could not read song information from this file",
            ErrorCategory.ARTWORK_PROCESSING: "There was a problem processing the artwork",
            ErrorCategory.MUSICBRAINZ_API: "Could not search for artwork online",
            ErrorCategory.NETWORK_ERROR: "Network connection problem",
            ErrorCategory.STORAGE_ERROR: "Could not save the processed file",
            ErrorCategory.SYSTEM_ERROR: "An unexpected system error occurred"
        }
        
        base_message = category_messages.get(error.category, error.message)
        
        if error.file_path:
            return f"{base_message} ({error.file_path.name})"
        
        return base_message
    
    def clear_errors(self):
        """Clear all stored errors"""
        self.errors.clear()
        for category in ErrorCategory:
            self.error_counts[category] = 0
        self.should_stop_processing = False
    
    def export_error_log(self, file_path: Path):
        """Export detailed error log to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("MP3 Artwork Manager - Error Log\n")
                f.write("=" * 50 + "\n\n")
                
                summary = self.get_error_summary()
                f.write(f"Total Errors: {summary['total_errors']}\n")
                f.write(f"Critical: {summary['error_counts_by_severity']['critical']}\n")
                f.write(f"High: {summary['error_counts_by_severity']['high']}\n")
                f.write(f"Medium: {summary['error_counts_by_severity']['medium']}\n")
                f.write(f"Low: {summary['error_counts_by_severity']['low']}\n\n")
                
                f.write("Detailed Error List:\n")
                f.write("-" * 30 + "\n")
                
                for error in sorted(self.errors, key=lambda x: x.timestamp):
                    f.write(f"\nTimestamp: {time.ctime(error.timestamp)}\n")
                    f.write(f"Category: {error.category.value}\n")
                    f.write(f"Severity: {error.severity.value}\n")
                    f.write(f"File: {error.file_path}\n")
                    f.write(f"Message: {error.message}\n")
                    if error.details:
                        f.write(f"Details: {error.details}\n")
                    if error.exception:
                        f.write(f"Exception: {traceback.format_exception_only(type(error.exception), error.exception)}\n")
                    f.write("-" * 30 + "\n")
                
            logger.info(f"Error log exported to: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export error log: {e}")

# Global error handler instance
error_handler = ErrorHandler() 