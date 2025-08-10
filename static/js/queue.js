// MP3 Artwork Manager - Queue functionality
class QueueManager {
    constructor() {
        this.refreshBtn = document.getElementById('refresh-queue');
        this.processAllBtn = document.getElementById('process-all');
        this.queueEmpty = document.getElementById('queue-empty');
        this.queueTable = document.getElementById('queue-table');
        this.queueTbody = document.getElementById('queue-tbody');
        this.files = [];
        
        this.initEventListeners();
        this.loadQueue();
        
        // Auto-refresh every 5 seconds
        this.autoRefreshInterval = setInterval(() => this.loadQueue(), 5000);
    }
    
    initEventListeners() {
        this.refreshBtn.addEventListener('click', () => this.loadQueue());
        this.processAllBtn.addEventListener('click', () => this.processAll());
    }
    
    async loadQueue() {
        try {
            const response = await fetch('/api/queue');
            if (response.ok) {
                const queue = await response.json();
                this.renderQueue(queue);
            } else {
                console.error('Failed to load queue');
            }
        } catch (error) {
            console.error('Error loading queue:', error);
        }
    }
    
    renderQueue(queue) {
        this.files = queue;
        if (!queue || queue.length === 0) {
            this.queueEmpty.style.display = 'block';
            this.queueTable.style.display = 'none';
            this.processAllBtn.disabled = true;
            return;
        }
        
        this.queueEmpty.style.display = 'none';
        this.queueTable.style.display = 'block';
        this.processAllBtn.disabled = false;
        
        this.queueTbody.innerHTML = '';
        
        queue.forEach(file => {
            const row = this.createFileRow(file);
            this.queueTbody.appendChild(row);
        });
    }
    
    createFileRow(file) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div class="text-truncate" style="max-width: 200px;" title="${file.filename}">
                    <i class="fas fa-music me-2"></i>${file.filename}
                </div>
            </td>
            <td>${this.formatFileSize(file.size)}</td>
            <td>
                <span class="badge status-badge status-${file.status}">
                    ${this.getStatusIcon(file.status)} ${file.status.toUpperCase()}
                </span>
            </td>
            <td>
                ${this.renderProgress(file)}
            </td>
            <td>
                ${this.renderArtwork(file)}
            </td>
            <td>
                ${this.renderActions(file)}
            </td>
        `;
        return row;
    }
    
    renderProgress(file) {
        if (file.status === 'processing') {
            const progress = file.progress || 0;
            return `
                <div class="progress">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: ${progress}%">
                        ${progress}%
                    </div>
                </div>
            `;
        } else if (file.status === 'completed') {
            return '<span class="text-success"><i class="fas fa-check"></i> Complete</span>';
        } else if (file.status === 'error') {
            return '<span class="text-danger"><i class="fas fa-exclamation-triangle"></i> Error</span>';
        }
        return '-';
    }
    
    renderArtwork(file) {
        if (file.artwork_options && file.artwork_options.length > 0) {
            const artworkCount = file.artwork_options.length;
            const selectedArtwork = file.selected_artwork;
            
            if (selectedArtwork) {
                return `
                    <div class="artwork-preview-container">
                        <img src="${selectedArtwork.preview_url}" 
                             class="artwork-preview" 
                             alt="Selected artwork">
                        <div class="artwork-preview-overlay">
                            <i class="fas fa-check"></i>
                        </div>
                    </div>
                `;
            } else {
                return `
                    <button class="btn btn-sm btn-outline-primary" 
                            onclick="queueManager.selectArtwork('${file.id}')">
                        <i class="fas fa-image me-1"></i>Choose (${artworkCount})
                    </button>
                `;
            }
        } else if (file.status === 'completed') {
            return '<span class="text-muted">No artwork</span>';
        }
        return '-';
    }
    
    renderActions(file) {
        const actions = [];
        
        if (file.status === 'pending') {
            actions.push(`
                <button class="btn btn-sm btn-primary me-1" 
                        onclick="queueManager.processFile('${file.id}')">
                    <i class="fas fa-play"></i>
                </button>
            `);
        }
        
        if (file.status === 'completed') {
            actions.push(`
                <button class="btn btn-sm btn-success me-1" 
                        onclick="queueManager.downloadFile('${file.id}')">
                    <i class="fas fa-download"></i>
                </button>
            `);
        }
        
        if (file.status !== 'processing') {
            actions.push(`
                <button class="btn btn-sm btn-outline-danger" 
                        onclick="queueManager.removeFile('${file.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            `);
        }
        
        return actions.join('');
    }
    
    getStatusIcon(status) {
        const icons = {
            'pending': 'fas fa-clock',
            'processing': 'fas fa-spinner fa-spin',
            'completed': 'fas fa-check',
            'error': 'fas fa-exclamation-triangle'
        };
        return `<i class="${icons[status] || 'fas fa-question'}"></i>`;
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async processFile(fileId) {
        try {
            const response = await fetch(`/api/process/${fileId}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.loadQueue(); // Refresh the queue
            } else {
                const error = await response.json();
                alert('Processing failed: ' + (error.message || 'Unknown error'));
            }
        } catch (error) {
            alert('Processing failed: ' + error.message);
        }
    }
    
    async processAll() {
        try {
            const response = await fetch('/api/process/batch', {
                method: 'POST'
            });
            
            if (response.ok) {
                this.loadQueue(); // Refresh the queue
            } else {
                const error = await response.json();
                alert('Batch processing failed: ' + (error.message || 'Unknown error'));
            }
        } catch (error) {
            alert('Batch processing failed: ' + error.message);
        }
    }
    
    async removeFile(fileId) {
        if (!confirm('Are you sure you want to remove this file?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/queue/${fileId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.loadQueue(); // Refresh the queue
            } else {
                const error = await response.json();
                alert('Remove failed: ' + (error.message || 'Unknown error'));
            }
        } catch (error) {
            alert('Remove failed: ' + error.message);
        }
    }
    
    selectArtwork(fileId) {
        // Navigate to artwork selection page
        window.location.href = `/artwork-selection?file_id=${fileId}`;
    }
    
    async downloadFile(fileId) {
        try {
            // First check if output file exists, if not generate it
            const fileObj = this.files.find(f => f.id === fileId);
            if (!fileObj) {
                alert('File not found');
                return;
            }
            
            if (!fileObj.output_path) {
                // Generate output file first
                const generateBtn = document.querySelector(`[data-file-id="${fileId}"] .btn-success`);
                if (generateBtn) {
                    generateBtn.disabled = true;
                    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';
                }
                
                const response = await fetch(`/api/output/${fileId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const result = await response.json();
                    this.showSuccess(`Output generated for ${fileObj.filename}`);
                    
                    // Update file object
                    fileObj.output_path = result.output_filename;
                    fileObj.output_size = result.output_size;
                    
                    // Refresh the display
                    this.updateFileCard(fileObj);
                } else {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to generate output');
                }
                
                if (generateBtn) {
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = '<i class="fas fa-download me-1"></i>Download';
                }
            }
            
            // Download the file
            window.open(`/api/download/${fileId}`, '_blank');
            
        } catch (error) {
            console.error('Download failed:', error);
            alert('Download failed: ' + error.message);
        }
    }
    
    async generateOutput(fileId) {
        try {
            const fileObj = this.files.find(f => f.id === fileId);
            if (!fileObj) {
                alert('File not found');
                return;
            }
            
            if (!fileObj.selected_artwork) {
                alert('Please select artwork first');
                return;
            }
            
            const generateBtn = document.querySelector(`[data-file-id="${fileId}"] .btn-success`);
            if (generateBtn) {
                generateBtn.disabled = true;
                generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';
            }
            
            const response = await fetch(`/api/output/${fileId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showSuccess(`Output generated: ${result.output_filename}`);
                
                // Update file object
                fileObj.output_path = result.output_filename;
                fileObj.output_size = result.output_size;
                fileObj.status = 'completed';
                
                // Refresh the display
                this.updateFileCard(fileObj);
                
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to generate output');
            }
            
        } catch (error) {
            console.error('Generate output failed:', error);
            alert('Generate output failed: ' + error.message);
            
            const generateBtn = document.querySelector(`[data-file-id="${fileId}"] .btn-success`);
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="fas fa-download me-1"></i>Download';
            }
        }
    }
    
    destroy() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
    }
}

// Initialize queue manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.queueManager = new QueueManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.queueManager) {
        window.queueManager.destroy();
    }
});
