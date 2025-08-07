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
            uploadedFiles = result.files;
            showStatusMessage(`Successfully uploaded ${result.total_files} files`, 'success');
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
 * Display the list of uploaded files
 */
function displayFileList() {
    const fileList = document.getElementById('fileList');
    if (!fileList) return;
    
    fileList.innerHTML = '';
    
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
                <div class="file-name">${file.original_filename}</div>
                <div class="file-metadata">${metadata.length > 0 ? metadata.join(' • ') : 'No metadata available'}</div>
                ${file.error ? `<div class="file-error" style="color: #dc3545; font-size: 0.8rem;">${file.error}</div>` : ''}
            </div>
            <div class="file-actions">
                <button class="btn-artwork" onclick="showArtworkOptions('${currentSession}', ${index})" title="Select artwork">
                    🎨 Select Artwork
                </button>
            </div>
            <div class="file-status status-${file.status}">${file.status}</div>
        `;
        
        fileList.appendChild(fileItem);
    });
}

/**
 * Process the uploaded files
 */
async function processFiles() {
    if (!currentSession) {
        showStatusMessage('No files to process', 'error');
        return;
    }
    
    if (isProcessing) {
        showStatusMessage('Already processing files', 'error');
        return;
    }
    
    isProcessing = true;
    showSection('processingSection');
    updateProgress(0, 'Starting processing...');
    
    try {
        const response = await fetch(`/process/${currentSession}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            updateProgress(100, 'Processing completed');
            showStatusMessage('Processing completed successfully', 'success');
            displayResults(result);
            showSection('resultsSection');
        } else {
            showStatusMessage(result.error || 'Processing failed', 'error');
        }
    } catch (error) {
        showStatusMessage('Processing failed: ' + error.message, 'error');
    } finally {
        isProcessing = false;
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
 * Show status message to user
 */
function showStatusMessage(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    const statusMessages = document.getElementById('statusMessages');
    if (!statusMessages) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `status-message status-${type}`;
    messageElement.textContent = message;
    
    statusMessages.appendChild(messageElement);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageElement.parentNode) {
            messageElement.parentNode.removeChild(messageElement);
        }
    }, 5000);
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
        showMessage('Failed to get artwork options', 'error');
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
                             <p>Size: ${formatFileSize(data.current_artwork.size_bytes)}</p>
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
        showMessage('Loading preview...', 'info');
        
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
        hideMessage();
    } catch (error) {
        console.error('Error previewing artwork:', error);
        showMessage('Failed to preview artwork', 'error');
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
        
        showMessage(skipArtwork ? 'Artwork skipped' : 'Artwork selected', 'success');
        closeArtworkModal();
        
        // Update file status to show user has made a choice
        updateFileArtworkStatus(fileIndex, skipArtwork ? 'skipped' : 'selected');
        
    } catch (error) {
        console.error('Error selecting artwork:', error);
        showMessage('Failed to select artwork', 'error');
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