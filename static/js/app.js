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
    
    uploadedFiles.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
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