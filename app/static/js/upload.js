// app/static/js/upload.js

class FileUploadManager {
    constructor() {
        this.files = new Map();
        this.uploadZone = document.getElementById('upload-zone');
        this.fileInput = document.getElementById('file-input');
        this.fileList = document.getElementById('file-list');
        this.fileSelectBtn = document.getElementById('file-select-btn');
        this.messageInput = document.getElementById('message-input');  // Add this
        this.maxFiles = 5;
        this.maxTotalSize = 30 * 1024 * 1024; // 30MB
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Drag and drop handlers
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        this.uploadZone.addEventListener('dragenter', () => this.handleDragEnter());
        this.uploadZone.addEventListener('dragover', () => this.handleDragOver());
        this.uploadZone.addEventListener('dragleave', () => this.handleDragLeave());
        this.uploadZone.addEventListener('drop', (e) => this.handleDrop(e));
        
        // File input handler
        this.fileSelectBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', () => this.handleFileSelect());
    }

    handleDragEnter() {
        // Get currentConversationId from window scope (from chat.js)
        if (!window.currentConversationId || this.isUploadDisabled()) return;
        this.uploadZone.classList.add('drag-over');
    }
    
    handleDragOver() {
        if (!window.currentConversationId || this.isUploadDisabled()) return;
        this.uploadZone.classList.add('drag-over');
    }
    
    handleDragLeave() {
        this.uploadZone.classList.remove('drag-over');
    }
    
    async handleDrop(e) {
        if (!window.currentConversationId || this.isUploadDisabled()) return;
        this.uploadZone.classList.remove('drag-over');
        
        const droppedFiles = [...e.dataTransfer.files];
        await this.processFiles(droppedFiles);
    }
    
    async handleFileSelect() {
        if (!window.currentConversationId || this.isUploadDisabled()) return;
        const selectedFiles = [...this.fileInput.files];
        await this.processFiles(selectedFiles);
        this.fileInput.value = ''; // Clear input
    }
    
    async processFiles(files) {
        // Validate file count
        if (this.files.size + files.length > this.maxFiles) {
            this.showNotification('Maximum 5 files allowed', 'error');
            return;
        }
        
        // Validate total size
        const totalSize = [...this.files.values()].reduce((sum, file) => sum + file.size, 0) +
            files.reduce((sum, file) => sum + file.size, 0);
            
        if (totalSize > this.maxTotalSize) {
            this.showNotification('Total file size exceeds 30MB', 'error');
            return;
        }
        
        // Validate file types
        const allowedTypes = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/csv'
        ];
        
        for (const file of files) {
            if (!allowedTypes.includes(file.type)) {
                this.showNotification(`File type not allowed: ${file.name}`, 'error');
                return;
            }
        }
        
        // Add files to list
        for (const file of files) {
            const fileId = crypto.randomUUID();
            this.files.set(fileId, file);
            this.addFileToList(fileId, file);
        }
        
        this.updateUploadZoneState();
    }
    
    addFileToList(fileId, file) {
        if (this.fileList.classList.contains('d-none')) {
            this.fileList.classList.remove('d-none');
        }
        
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <i class="bi bi-file-earmark file-icon"></i>
            <div class="file-info">
                <p class="file-name">${file.name}</p>
                <span class="file-size">${this.formatFileSize(file.size)}</span>
            </div>
            <button class="file-remove" data-file-id="${fileId}">
                <i class="bi bi-x"></i>
            </button>
        `;
        
        fileItem.querySelector('.file-remove').addEventListener('click', () => {
            this.removeFile(fileId);
        });
        
        this.fileList.appendChild(fileItem);
    }
    
    removeFile(fileId) {
        this.files.delete(fileId);
        this.fileList.querySelector(`[data-file-id="${fileId}"]`).closest('.file-item').remove();
        
        if (this.files.size === 0) {
            this.fileList.classList.add('d-none');
        }
        
        this.updateUploadZoneState();
    }
    
    async uploadFiles() {
        if (this.files.size === 0) return null;
        
        const formData = new FormData();
        const fileDetails = [];  // Add this to track files being uploaded
        
        this.files.forEach((file, fileId) => {
            formData.append('files', file);
            fileDetails.push({
                id: fileId,
                name: file.name,
                size: file.size
            });
        });
        
        formData.append('conversation_id', window.currentConversationId);
        
        try {
            // Show upload progress notification
            this.showNotification(
                `Uploading ${this.files.size} file(s)...`, 
                'info');
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${sessionStorage.getItem('token')}`
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('File upload failed');
            }
            
            const uploadedFiles = await response.json();
            
            // Update notification to show success
            this.showNotification(
                `Successfully uploaded ${this.files.size} file(s)`,
                'success'
            );
            
            // Keep track of uploaded file IDs but don't clear the UI yet
            // This allows the chat submission to use the file information
            const uploadedFileIds = uploadedFiles.map(file => file.id);
            
            return uploadedFileIds;
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Failed to upload files', 'error');
            throw error;
        }
    }

    showNotification(message, type = 'info') {
        const toast = $('#notification-toast');
        toast.find('.toast-body').text(message);
        toast.removeClass('bg-success bg-danger bg-info')
             .addClass(`bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'}`);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
    
    isUploadDisabled() {
        // Upload should be enabled when:
        // 1. We have a current conversation ID, and
        // 2. Message input is not disabled (no response being generated), and
        // 3. Either:
        //    a) It's a new conversation (no messages), or
        //    b) We already have files selected for this conversation
        return !window.currentConversationId || 
               $(this.messageInput).prop('disabled') ||
               (this.files.size === 0 && $('#chat-messages').children().length > 0);
    }
    
    updateUploadZoneState() {
        const isDisabled = this.isUploadDisabled();
        this.uploadZone.classList.toggle('disabled', isDisabled);
        this.fileInput.disabled = isDisabled;
        this.fileSelectBtn.disabled = isDisabled;
        
        // Add visual cue for new conversations or when files are already selected
        if (!isDisabled) {
            this.uploadZone.classList.add('active-upload-zone');
        } else {
            this.uploadZone.classList.remove('active-upload-zone');
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Add this new method to explicitly check if it's a new conversation
    isNewConversation() {
        return window.currentConversationId && 
                $('#chat-messages').children().length === 0;
    }

    reset() {
        // Clear all selected files
        this.files.clear();
        
        // Clear file input
        if (this.fileInput) {
            this.fileInput.value = '';
        }
        
        // Clear file list display
        if (this.fileList) {
            this.fileList.innerHTML = '';
            this.fileList.classList.add('d-none');
        }
        
        // Remove any states
        this.uploadZone.classList.remove('drag-over', 'active-upload-zone');
        
        // Update upload zone state
        this.updateUploadZoneState();
    }

    // Add helper method to check if files are ready to be sent
    hasReadyFiles() {
        return this.files.size > 0;
    }

    // Add helper method to get current file count
    getFileCount() {
        return this.files.size;
    }

    // Add method to get total size of selected files
    getTotalSize() {
        return Array.from(this.files.values())
            .reduce((total, file) => total + file.size, 0);
    }
}

// Only create the upload manager if we're on the chat page
if (document.getElementById('upload-zone')) {
    // Expose uploadManager to window scope so chat.js can access it
    window.uploadManager = new FileUploadManager();
}