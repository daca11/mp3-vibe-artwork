// MP3 Artwork Manager - Upload functionality
class UploadManager {
    constructor() {
        this.files = [];
        this.uploadArea = document.getElementById('upload-area');
        this.fileInput = document.getElementById('file-input');
        this.selectFilesBtn = document.getElementById('select-files');
        this.uploadBtn = document.getElementById('upload-btn');
        this.clearBtn = document.getElementById('clear-btn');
        this.fileList = document.getElementById('file-list');
        this.selectedFiles = document.getElementById('selected-files');
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Drag and drop events
        this.uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        this.uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        
        // File input events
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        this.selectFilesBtn.addEventListener('click', () => this.fileInput.click());
        
        // Button events
        this.uploadBtn.addEventListener('click', this.uploadFiles.bind(this));
        this.clearBtn.addEventListener('click', this.clearFiles.bind(this));
    }
    
    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }
    
    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        this.addFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.addFiles(files);
    }
    
    addFiles(files) {
        const mp3Files = files.filter(file => {
            const isMP3 = file.type === 'audio/mpeg' || file.name.toLowerCase().endsWith('.mp3');
            const isValidSize = file.size <= 50 * 1024 * 1024; // 50MB
            
            if (!isMP3) {
                this.showError(`${file.name} is not a valid MP3 file`);
                return false;
            }
            
            if (!isValidSize) {
                this.showError(`${file.name} is too large (max 50MB)`);
                return false;
            }
            
            return true;
        });
        
        // Add files to the list (avoid duplicates)
        mp3Files.forEach(file => {
            if (!this.files.some(f => f.name === file.name && f.size === file.size)) {
                this.files.push(file);
            }
        });
        
        this.updateFileList();
    }
    
    updateFileList() {
        if (this.files.length === 0) {
            this.fileList.style.display = 'none';
            this.uploadBtn.disabled = true;
            return;
        }
        
        this.fileList.style.display = 'block';
        this.uploadBtn.disabled = false;
        
        this.selectedFiles.innerHTML = '';
        
        this.files.forEach((file, index) => {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.innerHTML = `
                <div>
                    <strong>${file.name}</strong>
                    <br>
                    <small class="text-muted">${this.formatFileSize(file.size)}</small>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="uploadManager.removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            `;
            this.selectedFiles.appendChild(li);
        });
    }
    
    removeFile(index) {
        this.files.splice(index, 1);
        this.updateFileList();
    }
    
    clearFiles() {
        this.files = [];
        this.fileInput.value = '';
        this.updateFileList();
    }
    
    async uploadFiles() {
        if (this.files.length === 0) return;
        
        this.uploadBtn.disabled = true;
        this.uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Uploading...';
        
        try {
            const formData = new FormData();
            this.files.forEach(file => {
                formData.append('files', file);
            });
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showSuccess(`Successfully uploaded ${this.files.length} file(s)`);
                this.clearFiles();
                
                // Redirect to queue page
                setTimeout(() => {
                    window.location.href = '/queue';
                }, 2000);
            } else {
                const error = await response.json();
                this.showError(error.message || 'Upload failed');
            }
        } catch (error) {
            this.showError('Upload failed: ' + error.message);
        } finally {
            this.uploadBtn.disabled = false;
            this.uploadBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Upload Files';
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    showError(message) {
        this.showMessage(message, 'danger');
    }
    
    showSuccess(message) {
        this.showMessage(message, 'success');
    }
    
    showMessage(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.querySelector('main').insertBefore(alert, document.querySelector('main').firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
}

// Initialize upload manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.uploadManager = new UploadManager();
});
