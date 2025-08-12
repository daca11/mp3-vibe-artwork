// MP3 Artwork Manager - Queue functionality
class QueueManager {
    constructor() {
        this.refreshBtn = document.getElementById('refresh-queue');
        this.processAllBtn = document.getElementById('process-all');
        this.clearQueueBtn = document.getElementById('clear-queue');
        this.downloadAllBtn = document.getElementById('download-all');
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
        this.clearQueueBtn.addEventListener('click', () => this.clearQueue());
        this.downloadAllBtn.addEventListener('click', () => this.downloadAll());
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
            this.clearQueueBtn.disabled = true;
            this.downloadAllBtn.disabled = true;
            return;
        }
        
        this.queueEmpty.style.display = 'none';
        this.queueTable.style.display = 'block';
        
        const hasPending = queue.some(file => file.status === 'pending');
        this.processAllBtn.disabled = !hasPending;
        
        const hasCompleted = queue.some(file => file.status === 'completed');
        this.downloadAllBtn.disabled = !hasCompleted;

        this.clearQueueBtn.disabled = false;
        
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
    
    showSuccess(message) {
        alert(message);
    }
    
    showError(message) {
        alert(message);
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
                this.showError('Processing failed: ' + (error.message || 'Unknown error'));
            }
        } catch (error) {
            this.showError('Processing failed: ' + error.message);
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
                this.showError('Batch processing failed: ' + (error.message || 'Unknown error'));
            }
        } catch (error) {
            this.showError('Batch processing failed: ' + error.message);
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
                this.showError('Remove failed: ' + (error.message || 'Unknown error'));
            }
        } catch (error) {
            this.showError('Remove failed: ' + error.message);
        }
    }
    
    async clearQueue() {
        if (!confirm('Are you sure you want to clear the entire queue? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/api/queue/clear', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadQueue(); // Refresh the queue
            } else {
                const error = await response.json();
                this.showError('Failed to clear queue: ' + (error.message || 'Unknown error'));
            }
        } catch (error) {
            this.showError('Failed to clear queue: ' + error.message);
        }
    }

    selectArtwork(fileId) {
        // Navigate to artwork selection page
        window.location.href = `/artwork-selection?file_id=${fileId}`;
    }
    
    async downloadFile(fileId) {
        try {
            const fileObj = this.files.find(f => f.id === fileId);
            if (!fileObj) {
                this.showError('File not found');
                return;
            }
            
            // If output path doesn't exist, generate it first
            if (!fileObj.output_path || !fileObj.output_path.trim()) {
                const generateBtn = document.querySelector(`button[onclick="queueManager.downloadFile('${fileId}')"]`);
                if (generateBtn) {
                    generateBtn.disabled = true;
                    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';
                }
                
                const response = await fetch(`/api/output/${fileId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (response.ok) {
                    // Refresh the queue to get the new output_path
                    await this.loadQueue(); 
                } else {
                    const error = await response.json();
                    this.showError(`Failed to generate file: ${error.error || 'Unknown error'}`);
                    await this.loadQueue(); // Refresh even on error
                    return;
                }
            }
            
            // Re-check after generation attempt
            const updatedFileObj = this.files.find(f => f.id === fileId);
            if (updatedFileObj && updatedFileObj.output_path) {
                window.open(`/api/download/${fileId}`, '_blank');
            } else {
                this.showError('File generation did not complete. Please try again.');
            }
            
        } catch (error) {
            console.error('Download failed:', error);
            this.showError('Download failed: ' + error.message);
            await this.loadQueue();
        }
    }

    async downloadAll() {
        try {
            // Step 1: Tell the backend to generate all missing output files
            this.downloadAllBtn.disabled = true;
            this.downloadAllBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';

            const fileIdsToGenerate = this.files
                .filter(f => f.status === 'completed' && (!f.output_path || !f.output_path.trim()))
                .map(f => f.id);

            if (fileIdsToGenerate.length > 0) {
                const response = await fetch('/api/output/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file_ids: fileIdsToGenerate })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(`Batch generation failed: ${error.error || 'Unknown error'}`);
                }
            }

            // Step 2: Refresh queue and then trigger download
            await this.loadQueue();
            
            // Check if there are any downloadable files
            const hasDownloadableFiles = this.files.some(f => f.status === 'completed' && f.output_path);

            if (hasDownloadableFiles) {
                window.open('/api/download/all', '_blank');
            } else {
                this.showError('No files were generated. Please check for errors or artwork selections.');
            }

        } catch (error) {
            console.error('Download All failed:', error);
            this.showError(`Download All failed: ${error.message}`);
        } finally {
            this.downloadAllBtn.disabled = false;
            this.downloadAllBtn.innerHTML = '<i class="fas fa-download me-1"></i>Download All';
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
