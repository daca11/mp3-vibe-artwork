/**
 * MP3 Artwork Manager - Main JavaScript
 * Handles client-side functionality and user interactions
 */

// Global variables
let currentSession = null;
let uploadedFiles = [];
let isProcessing = false;

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('MP3 Artwork Manager loaded');
    
    // Initialize the application
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    setupFileUpload();
    setupEventListeners();
    showStatusMessage('Application ready', 'info');
}

/**
 * Setup file upload functionality
 */
function setupFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const selectFilesBtn = document.getElementById('selectFilesBtn');
    
    if (!uploadArea || !fileInput || !selectFilesBtn) {
        console.error('Upload elements not found');
        return;
    }
    
    // Click to select files
    selectFilesBtn.addEventListener('click', () => {
        fileInput.click();
    });
    
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Process files button
    const processBtn = document.getElementById('processBtn');
    if (processBtn) {
        processBtn.addEventListener('click', processFiles);
    }
    
    // Clear files button
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearFiles);
    }
    
    // Download button
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadFiles);
    }
    
    // Start over button
    const startOverBtn = document.getElementById('startOverBtn');
    if (startOverBtn) {
        startOverBtn.addEventListener('click', startOver);
    }
}

/**
 * Handle file selection
 */
function handleFiles(files) {
    const fileArray = Array.from(files);
    const mp3Files = fileArray.filter(file => Utils.isValidMP3File(file));
    
    if (mp3Files.length === 0) {
        showStatusMessage('No valid MP3 files selected', 'error');
        return;
    }
    
    if (fileArray.length > mp3Files.length) {
        showStatusMessage(`${fileArray.length - mp3Files.length} non-MP3 files were filtered out`, 'info');
    }
    
    uploadFiles(mp3Files);
}

/**
 * Upload files to the server
 */
async function uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });
    
    try {
        showStatusMessage('Uploading files...', 'info');
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            currentSession = result.session_id;
            // Backend doesn't return files array, we'll fetch it via status endpoint
            uploadedFiles = [];
            showStatusMessage(`Successfully uploaded ${result.files_uploaded} files`, 'success');
            
            // Fetch the actual file list from the session status
            await fetchFileList();
            displayFileList();
            showSection('fileListSection');
        } else {
            showStatusMessage(result.error || 'Upload failed', 'error');
        }
    } catch (error) {
        showStatusMessage('Upload failed: ' + error.message, 'error');
    }
}

/**
 * Fetch file list from session status
 */
async function fetchFileList() {
    if (!currentSession) {
        return;
    }
    
    try {
        const response = await fetch(`/status/${currentSession}`);
        const sessionData = await response.json();
        
        if (response.ok && sessionData.files) {
            uploadedFiles = sessionData.files;
        } else {
            console.warn('No files in session data:', sessionData);
            uploadedFiles = [];
        }
    } catch (error) {
        console.error('Error fetching file list:', error);
        uploadedFiles = [];
    }
}

/**
 * Display the list of uploaded files
 */
function displayFileList() {
    const fileList = document.getElementById('fileList');
    if (!fileList) return;
    
    fileList.innerHTML = '';
    
    // Safety check for uploadedFiles
    if (!uploadedFiles || !Array.isArray(uploadedFiles)) {
        fileList.innerHTML = '<p>No files uploaded yet.</p>';
        return;
    }
    
    uploadedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.setAttribute('data-file-index', index);
        
        const metadata = [];
        if (file.artist) metadata.push(`Artist: ${file.artist}`);
        if (file.title) metadata.push(`Title: ${file.title}`);
        if (file.album) metadata.push(`Album: ${file.album}`);
        
        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-name">${file.filename || file.original_filename || 'Unknown file'}</div>
                <div class="file-metadata">${metadata.length > 0 ? metadata.join(' • ') : 'Metadata will be extracted during processing'}</div>
                <div class="file-size">${Utils.formatFileSize(file.size || 0)}</div>
                ${file.error ? `<div class="file-error" style="color: #dc3545; font-size: 0.8rem;">${file.error}</div>` : ''}
            </div>
            <div class="file-actions">
                <button class="btn-artwork" onclick="showArtworkOptions('${currentSession}', ${index})" title="Select artwork">
                    🎨 Select Artwork
                </button>
            </div>
            <div class="file-status status-${file.status || 'uploaded'}">${Utils.formatStatus(file.status || 'uploaded')}</div>
        `;
        
        fileList.appendChild(fileItem);
    });
}

/**
 * Process the uploaded files with enhanced progress tracking
 */
async function processFiles() {
    if (!currentSession) {
        showStatusMessage('No files to process', 'error');
        return;
    }

    try {
        // Start progress tracking
        startProgressTracking(currentSession);
        
        // Show progress UI
        showProgressUI();
        
        const response = await fetch(`/process/${currentSession}`, {
            method: 'POST'
        });

        const result = await response.json();
        
        if (response.ok) {
            showStatusMessage(result.message, 'success');
            
            // Show download link if processing was successful
            if (result.summary && result.summary.successful > 0) {
                showDownloadLink();
            }
        } else {
            showStatusMessage(result.error || 'Processing failed', 'error');
            
            // Show error details if available
            if (result.error_summary && result.error_summary.total_errors > 0) {
                setTimeout(() => showErrorLog(), 1000);
            }
        }
    } catch (error) {
        console.error('Error processing files:', error);
        showStatusMessage('Processing failed', 'error');
        stopProgressTracking();
    }
}

function showProgressUI() {
    const progressContainer = document.getElementById('progress-container');
    
    if (!progressContainer) {
        // Create progress UI if it doesn't exist
        const container = document.createElement('div');
        container.id = 'progress-container';
        container.innerHTML = `
            <div class="progress-section">
                <h3>Processing Files</h3>
                
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                
                <div class="progress-info">
                    <div id="progress-text">0/0 files (0%)</div>
                    <div id="current-operation">Initializing...</div>
                    <div id="time-remaining"></div>
                </div>
                
                <div class="processing-controls">
                    <button id="pause-btn" class="btn secondary" onclick="controlProcessing('pause')" style="display: inline-block;">⏸️ Pause</button>
                    <button id="resume-btn" class="btn secondary" onclick="controlProcessing('resume')" style="display: none;">▶️ Resume</button>
                    <button id="cancel-btn" class="btn danger" onclick="controlProcessing('cancel')" style="display: inline-block;">🛑 Cancel</button>
                    <button id="retry-btn" class="btn primary" onclick="controlProcessing('retry_errors')" style="display: none;">🔄 Retry Errors</button>
                    <button id="clear-queue-btn" class="btn secondary" onclick="controlProcessing('clear_queue')" style="display: none;">🗑️ Clear Queue</button>
                </div>
                
                <div id="error-container" class="error-container" style="display: none;">
                    <h4>Errors (<span id="error-count">0</span>)</h4>
                    <div id="error-list" class="error-list"></div>
                    <button class="btn secondary" onclick="showErrorLog()">📋 View Full Error Log</button>
                </div>
            </div>
        `;
        
        // Insert after upload section
        const uploadSection = document.querySelector('.upload-section');
        if (uploadSection) {
            uploadSection.insertAdjacentElement('afterend', container);
        }
    } else {
        progressContainer.style.display = 'block';
    }
}

/**
 * Update progress indicator
 */
function updateProgress(percentage, message) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const currentFileName = document.getElementById('currentFileName');
    
    if (progressFill) {
        progressFill.style.width = percentage + '%';
    }
    
    if (progressText) {
        progressText.textContent = `${percentage}% Complete`;
    }
    
    if (currentFileName && message) {
        currentFileName.textContent = message;
    }
}

/**
 * Display processing results
 */
function displayResults(results) {
    const resultsSummary = document.getElementById('resultsSummary');
    const resultsList = document.getElementById('resultsList');
    
    if (resultsSummary) {
        const successCount = results.results.filter(r => r.status === 'completed').length;
        const errorCount = results.results.filter(r => r.status === 'error').length;
        
        resultsSummary.innerHTML = `
            <h3>Processing Complete</h3>
            <p><strong>Total files:</strong> ${results.total_files}</p>
            <p><strong>Successful:</strong> ${successCount}</p>
            <p><strong>Errors:</strong> ${errorCount}</p>
        `;
    }
    
    if (resultsList) {
        resultsList.innerHTML = '';
        
        results.results.forEach(file => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            
            const processingInfo = file.processing_info || {};
            const statusDetails = [];
            
            if (processingInfo.artwork_processed) {
                statusDetails.push('Artwork optimized');
            }
            if (processingInfo.metadata_extracted) {
                statusDetails.push('Metadata preserved');
            }
            if (processingInfo.filename_parsed) {
                statusDetails.push('Filename parsed');
            }
            
            resultItem.innerHTML = `
                <div class="file-info">
                    <div class="file-name">${file.original_filename}</div>
                    <div class="file-metadata">
                        ${statusDetails.length > 0 ? statusDetails.join(' • ') : 'Basic processing'}
                    </div>
                    ${file.error ? `<div class="file-error" style="color: #dc3545; font-size: 0.8rem;">${file.error}</div>` : ''}
                </div>
                <div class="file-status status-${file.status}">${file.status}</div>
            `;
            
            resultsList.appendChild(resultItem);
        });
    }
}

/**
 * Download processed files
 */
async function downloadFiles() {
    if (!currentSession) {
        showStatusMessage('No session to download from', 'error');
        return;
    }
    
    try {
        window.location.href = `/download/${currentSession}`;
        showStatusMessage('Download started', 'success');
    } catch (error) {
        showStatusMessage('Download failed: ' + error.message, 'error');
    }
}

/**
 * Clear all files and start over
 */
function clearFiles() {
    uploadedFiles = [];
    currentSession = null;
    
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.value = '';
    }
    
    showSection('uploadSection');
    showStatusMessage('Files cleared', 'info');
}

/**
 * Start over with new files
 */
function startOver() {
    clearFiles();
}

/**
 * Show a specific section and hide others
 */
function showSection(sectionId) {
    const sections = ['uploadSection', 'fileListSection', 'processingSection', 'resultsSection'];
    
    sections.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.style.display = id === sectionId ? 'block' : 'none';
        }
    });
}

/**
 * Show status message to user with manual dismiss functionality
 */
function showStatusMessage(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    const statusMessages = document.getElementById('statusMessages');
    if (!statusMessages) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `status-message status-${type}`;
    
    // Create message content container
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = message;
    
    // Create dismiss button
    const dismissButton = document.createElement('button');
    dismissButton.className = 'message-dismiss';
    dismissButton.innerHTML = '✕';
    dismissButton.title = 'Dismiss notification';
    dismissButton.setAttribute('aria-label', 'Dismiss notification');
    
    // Add click handler for dismiss button
    dismissButton.addEventListener('click', () => {
        if (messageElement.parentNode) {
            messageElement.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (messageElement.parentNode) {
                    messageElement.parentNode.removeChild(messageElement);
                }
            }, 300);
        }
    });
    
    // Assemble message element
    messageElement.appendChild(messageContent);
    messageElement.appendChild(dismissButton);
    
    statusMessages.appendChild(messageElement);
    
    // No auto-dismissal - notifications persist until manually dismissed
}

/**
 * Utility functions
 */
const Utils = {
    /**
     * Format file size in human readable format
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * Validate MP3 file
     * @param {File} file - The file to validate
     * @returns {boolean} True if valid MP3 file
     */
    isValidMP3File: function(file) {
        const validTypes = ['audio/mp3', 'audio/mpeg'];
        const validExtensions = ['.mp3', '.MP3'];
        
        // Check MIME type
        if (validTypes.includes(file.type)) {
            return true;
        }
        
        // Check file extension as fallback
        const fileName = file.name.toLowerCase();
        return validExtensions.some(ext => fileName.endsWith(ext.toLowerCase()));
    },
    
    /**
     * Format status for display
     * @param {string} status - The status to format
     * @returns {string} Formatted status
     */
    formatStatus: function(status) {
        const statusMap = {
            'uploaded': 'Uploaded',
            'processing': 'Processing...',
            'completed': 'Completed',
            'failed': 'Failed',
            'pending': 'Pending',
            'error': 'Error'
        };
        
        return statusMap[status] || status.charAt(0).toUpperCase() + status.slice(1);
    }
}; 

// Phase 6: Artwork Preview and Selection Functions

async function showArtworkOptions(sessionId, fileIndex) {
    try {
        const response = await fetch(`/api/artwork-options/${sessionId}/${fileIndex}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to get artwork options');
        }
        
        displayArtworkModal(data, sessionId, fileIndex);
    } catch (error) {
        console.error('Error getting artwork options:', error);
        showStatusMessage('Failed to get artwork options', 'error');
    }
}

function displayArtworkModal(data, sessionId, fileIndex) {
    const modal = document.createElement('div');
    modal.className = 'artwork-modal';
    modal.innerHTML = `
        <div class="artwork-modal-content">
            <div class="artwork-modal-header">
                <h3>Select Artwork for ${data.file_info.filename}</h3>
                <button class="close-modal" onclick="closeArtworkModal()">&times;</button>
            </div>
            
            <div class="artwork-file-info">
                <p><strong>Artist:</strong> ${data.file_info.artist || 'Unknown'}</p>
                <p><strong>Title:</strong> ${data.file_info.title || 'Unknown'}</p>
                <p><strong>Album:</strong> ${data.file_info.album || 'Unknown'}</p>
            </div>
            
            <div class="artwork-current">
                <h4>Current Artwork</h4>
                ${data.current_artwork ? 
                    `<div class="artwork-preview">
                        <img src="${data.current_artwork.data_url}" alt="Current artwork" />
                                                 <div class="artwork-info">
                             <p>Format: ${data.current_artwork.format}</p>
                             <p>Size: ${Utils.formatFileSize(data.current_artwork.size_bytes)}</p>
                         </div>
                    </div>` : 
                    '<p class="no-artwork">No current artwork</p>'
                }
            </div>
            
            <div class="artwork-options">
                <h4>Available Options (${data.artwork_options.length} found)</h4>
                <div class="artwork-grid">
                    ${data.artwork_options.map((option, index) => `
                        <div class="artwork-option" data-index="${index}">
                            <div class="artwork-thumbnail">
                                <img src="${option.thumbnail_url || option.artwork_url}" 
                                     alt="Artwork option ${index + 1}"
                                     onclick="previewArtwork('${option.artwork_url}', ${index})" />
                                <div class="artwork-badges">
                                    ${option.is_front ? '<span class="badge front">Front</span>' : ''}
                                    ${option.approved ? '<span class="badge approved">Approved</span>' : ''}
                                </div>
                            </div>
                            <div class="artwork-details">
                                <p class="release-title">${option.release_title}</p>
                                <p class="release-artist">${option.release_artist}</p>
                                ${option.release_date ? `<p class="release-date">${option.release_date}</p>` : ''}
                                ${option.width && option.height ? 
                                    `<p class="dimensions">${option.width} × ${option.height}</p>` : ''}
                                ${option.comment ? `<p class="comment">${option.comment}</p>` : ''}
                            </div>
                            <button class="select-artwork-btn" 
                                    onclick="selectArtwork('${sessionId}', ${fileIndex}, '${option.artwork_url}')">
                                Select This Artwork
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="artwork-actions">
                <button class="btn secondary" onclick="selectArtwork('${sessionId}', ${fileIndex}, null, true)">
                    Skip Artwork
                </button>
                <button class="btn primary" onclick="closeArtworkModal()">
                    Cancel
                </button>
            </div>
            
            <div id="artwork-preview-area" class="artwork-preview-area" style="display: none;">
                <h4>Preview</h4>
                <div id="preview-content"></div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

async function previewArtwork(artworkUrl, optionIndex) {
    try {
        showStatusMessage('Loading preview...', 'info');
        
        const response = await fetch('/api/artwork-preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ artwork_url: artworkUrl })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to preview artwork');
        }
        
        displayArtworkPreview(data, optionIndex);
        // Note: Notifications now persist until manually dismissed
    } catch (error) {
        console.error('Error previewing artwork:', error);
        showStatusMessage('Failed to preview artwork', 'error');
    }
}

function displayArtworkPreview(previewData, optionIndex) {
    const previewArea = document.getElementById('artwork-preview-area');
    const previewContent = document.getElementById('preview-content');
    
    previewContent.innerHTML = `
        <div class="preview-comparison">
            <div class="preview-before">
                <h5>Original</h5>
                <div class="preview-stats">
                    <p>Size: ${formatFileSize(previewData.original_size_bytes)}</p>
                </div>
            </div>
            <div class="preview-after">
                <h5>After Processing</h5>
                <img src="${previewData.preview_data_url}" alt="Processed preview" />
                <div class="preview-stats">
                    <p>Size: ${formatFileSize(previewData.processed_size_bytes)}</p>
                    <p>Compliant: ${previewData.is_compliant ? 'Yes' : 'No'}</p>
                    ${previewData.was_resized ? '<p class="change">Resized</p>' : ''}
                    ${previewData.was_optimized ? '<p class="change">Optimized</p>' : ''}
                </div>
            </div>
        </div>
        <div class="preview-details">
            <h5>Processing Applied:</h5>
            <ul>
                ${previewData.processing_applied.map(action => `<li>${action}</li>`).join('')}
            </ul>
        </div>
    `;
    
    previewArea.style.display = 'block';
    previewArea.scrollIntoView({ behavior: 'smooth' });
}

async function selectArtwork(sessionId, fileIndex, artworkUrl, skipArtwork = false) {
    try {
        const response = await fetch(`/api/select-artwork/${sessionId}/${fileIndex}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                artwork_url: artworkUrl,
                skip_artwork: skipArtwork
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to select artwork');
        }
        
        showStatusMessage(skipArtwork ? 'Artwork skipped' : 'Artwork selected', 'success');
        closeArtworkModal();
        
        // Update file status to show user has made a choice
        updateFileArtworkStatus(fileIndex, skipArtwork ? 'skipped' : 'selected');
        
    } catch (error) {
        console.error('Error selecting artwork:', error);
        showStatusMessage('Failed to select artwork', 'error');
    }
}

function updateFileArtworkStatus(fileIndex, status) {
    const fileItem = document.querySelector(`[data-file-index="${fileIndex}"]`);
    if (fileItem) {
        const statusElement = fileItem.querySelector('.artwork-status');
        if (statusElement) {
            statusElement.textContent = status === 'selected' ? 'Artwork Selected' : 'Artwork Skipped';
            statusElement.className = `artwork-status ${status}`;
        } else {
            // Add status element if it doesn't exist
            const statusDiv = document.createElement('div');
            statusDiv.className = `artwork-status ${status}`;
            statusDiv.textContent = status === 'selected' ? 'Artwork Selected' : 'Artwork Skipped';
            fileItem.appendChild(statusDiv);
        }
    }
}

function closeArtworkModal() {
    const modal = document.querySelector('.artwork-modal');
    if (modal) {
        modal.remove();
    }
} 

// Phase 7: Enhanced Error Handling and Progress Tracking

// Global variables for progress tracking
let progressInterval = null;
let currentSessionId = null;

async function startProgressTracking(sessionId) {
    currentSessionId = sessionId;
    
    // Clear any existing interval
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    // Start progress tracking
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/processing-status/${sessionId}`);
            const status = await response.json();
            
            if (response.ok) {
                updateProgressDisplay(status);
                
                // Stop tracking if processing is complete
                if (['completed', 'completed_with_errors', 'failed', 'cancelled'].includes(status.status)) {
                    stopProgressTracking();
                    showProcessingComplete(status);
                }
            } else {
                console.error('Failed to get processing status:', status.error);
            }
        } catch (error) {
            console.error('Error tracking progress:', error);
        }
    }, 1000); // Update every second
}

function stopProgressTracking() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function updateProgressDisplay(status) {
    // Update progress bar
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const currentOperation = document.getElementById('current-operation');
    const timeRemaining = document.getElementById('time-remaining');
    
    if (progressBar) {
        progressBar.style.width = `${status.progress_percentage}%`;
        progressBar.setAttribute('aria-valuenow', status.progress_percentage);
    }
    
    if (progressText) {
        progressText.textContent = `${status.processed_files}/${status.total_files} files (${status.progress_percentage}%)`;
    }
    
    if (currentOperation) {
        currentOperation.textContent = status.current_operation || 'Processing...';
    }
    
    if (timeRemaining && status.estimated_time_remaining) {
        const minutes = Math.floor(status.estimated_time_remaining / 60);
        const seconds = status.estimated_time_remaining % 60;
        timeRemaining.textContent = `~${minutes}:${seconds.toString().padStart(2, '0')} remaining`;
    }
    
    // Update error information
    updateErrorDisplay(status.errors);
    
    // Update file statuses
    updateFileStatuses(status.files);
}

function updateErrorDisplay(errorSummary) {
    const errorContainer = document.getElementById('error-container');
    
    if (!errorContainer) return;
    
    if (errorSummary.total_errors > 0) {
        errorContainer.style.display = 'block';
        
        const errorCount = document.getElementById('error-count');
        const errorList = document.getElementById('error-list');
        
        if (errorCount) {
            errorCount.textContent = `${errorSummary.total_errors} errors`;
        }
        
        if (errorList && errorSummary.recent_errors) {
            errorList.innerHTML = errorSummary.recent_errors.map(error => `
                <div class="error-item ${error.severity}">
                    <span class="error-category">${error.category}</span>
                    <span class="error-message">${error.user_message || error.message}</span>
                    ${error.file_path ? `<span class="error-file">${error.file_path}</span>` : ''}
                </div>
            `).join('');
        }
    } else {
        errorContainer.style.display = 'none';
    }
}

function updateFileStatuses(files) {
    files.forEach((file, index) => {
        const fileElement = document.querySelector(`[data-file-index="${index}"]`);
        if (fileElement) {
            const statusElement = fileElement.querySelector('.file-status .status-text');
            if (statusElement) {
                statusElement.textContent = getStatusText(file.status);
                fileElement.className = `file-item ${file.status}`;
            }
            
            // Add error indicators
            if (file.errors && file.errors.length > 0) {
                const errorIndicator = fileElement.querySelector('.error-indicator') || 
                    document.createElement('div');
                errorIndicator.className = 'error-indicator';
                errorIndicator.innerHTML = `⚠️ ${file.errors.length} error(s)`;
                errorIndicator.title = file.errors.join('\n');
                fileElement.appendChild(errorIndicator);
            }
            
            // Add warning indicators
            if (file.warnings && file.warnings.length > 0) {
                const warningIndicator = fileElement.querySelector('.warning-indicator') || 
                    document.createElement('div');
                warningIndicator.className = 'warning-indicator';
                warningIndicator.innerHTML = `⚠️ ${file.warnings.length} warning(s)`;
                warningIndicator.title = file.warnings.join('\n');
                fileElement.appendChild(warningIndicator);
            }
        }
    });
}

async function controlProcessing(action) {
    if (!currentSessionId) {
        showStatusMessage('No active processing session', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/processing-controls/${currentSessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStatusMessage(result.message, 'success');
            
            // Update UI based on action
            if (action === 'pause') {
                updateProcessingControls('paused');
            } else if (action === 'resume') {
                updateProcessingControls('processing');
            } else if (action === 'cancel') {
                updateProcessingControls('cancelled');
                stopProgressTracking();
            } else if (action === 'retry_errors') {
                showStatusMessage('Retrying failed files...', 'info');
            } else if (action === 'clear_queue') {
                location.reload(); // Refresh page to show empty queue
            }
        } else {
            showStatusMessage(result.error || 'Failed to control processing', 'error');
        }
    } catch (error) {
        console.error('Error controlling processing:', error);
        showStatusMessage('Failed to control processing', 'error');
    }
}

function updateProcessingControls(status) {
    const pauseBtn = document.getElementById('pause-btn');
    const resumeBtn = document.getElementById('resume-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const retryBtn = document.getElementById('retry-btn');
    
    if (pauseBtn) pauseBtn.style.display = (status === 'processing') ? 'inline-block' : 'none';
    if (resumeBtn) resumeBtn.style.display = (status === 'paused') ? 'inline-block' : 'none';
    if (cancelBtn) cancelBtn.style.display = (['processing', 'paused'].includes(status)) ? 'inline-block' : 'none';
    if (retryBtn) retryBtn.style.display = (['completed_with_errors', 'failed'].includes(status)) ? 'inline-block' : 'none';
}

async function showErrorLog() {
    if (!currentSessionId) {
        showStatusMessage('No active session', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/error-log/${currentSessionId}`);
        const errorLog = await response.json();
        
        if (response.ok) {
            displayErrorLogModal(errorLog);
        } else {
            showStatusMessage(errorLog.error || 'Failed to get error log', 'error');
        }
    } catch (error) {
        console.error('Error getting error log:', error);
        showStatusMessage('Failed to get error log', 'error');
    }
}

function displayErrorLogModal(errorLog) {
    const modal = document.createElement('div');
    modal.className = 'error-log-modal';
    modal.innerHTML = `
        <div class="error-log-content">
            <div class="error-log-header">
                <h3>Error Log</h3>
                <button class="close-modal" onclick="closeErrorLogModal()">&times;</button>
            </div>
            
            <div class="error-summary">
                <h4>Summary</h4>
                <div class="summary-stats">
                    <div class="stat">
                        <span class="stat-label">Total Errors:</span>
                        <span class="stat-value">${errorLog.total_errors}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Critical:</span>
                        <span class="stat-value critical">${errorLog.error_counts_by_severity.critical}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">High:</span>
                        <span class="stat-value high">${errorLog.error_counts_by_severity.high}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Medium:</span>
                        <span class="stat-value medium">${errorLog.error_counts_by_severity.medium}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Low:</span>
                        <span class="stat-value low">${errorLog.error_counts_by_severity.low}</span>
                    </div>
                </div>
            </div>
            
            <div class="error-details">
                <h4>Recent Errors</h4>
                <div class="error-list">
                    ${errorLog.recent_errors.map(error => `
                        <div class="error-item ${error.severity}">
                            <div class="error-header">
                                <span class="error-category">${error.category}</span>
                                <span class="error-severity ${error.severity}">${error.severity}</span>
                                <span class="error-time">${new Date(error.timestamp * 1000).toLocaleString()}</span>
                            </div>
                            <div class="error-message">${error.user_message || error.message}</div>
                            ${error.file_path ? `<div class="error-file">File: ${error.file_path}</div>` : ''}
                            ${error.retry_count > 0 ? `<div class="error-retries">Retries: ${error.retry_count}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="error-actions">
                <button class="btn secondary" onclick="exportErrorLog()">Export Log</button>
                <button class="btn primary" onclick="closeErrorLogModal()">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

function closeErrorLogModal() {
    const modal = document.querySelector('.error-log-modal');
    if (modal) {
        modal.remove();
    }
}

async function exportErrorLog() {
    if (!currentSessionId) {
        showStatusMessage('No active session', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/export-error-log/${currentSessionId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Create and download the log file
            const blob = new Blob([result.log_content], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = result.filename;
            a.click();
            window.URL.revokeObjectURL(url);
            
            showStatusMessage('Error log exported successfully', 'success');
        } else {
            showStatusMessage(result.error || 'Failed to export error log', 'error');
        }
    } catch (error) {
        console.error('Error exporting error log:', error);
        showStatusMessage('Failed to export error log', 'error');
    }
}

function showProcessingComplete(status) {
    const summary = status.summary || {};
    
    let message = `Processing completed!\n`;
    message += `✅ ${summary.successful || 0} files processed successfully\n`;
    
    if (summary.failed > 0) {
        message += `❌ ${summary.failed} files failed\n`;
    }
    
    if (summary.warnings > 0) {
        message += `⚠️ ${summary.warnings} files with warnings\n`;
    }
    
    message += `⏱️ Processing time: ${summary.processing_time || 0} seconds`;
    
    if (summary.failed > 0 || summary.warnings > 0) {
        message += `\n\nClick 'View Error Log' for details.`;
    }
    
    // Update the UI to show completion
    const messageType = summary.failed > 0 ? 'warning' : 'success';
    showStatusMessage(message, messageType);
    
    // Show final processing controls
    updateProcessingControls(status.status);
} 