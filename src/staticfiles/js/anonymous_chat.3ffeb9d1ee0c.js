document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const filePreview = document.getElementById('file-preview');
    const form = document.getElementById('anonymous-chat-form');

    if (!dropArea || !fileInput || !filePreview || !form) {
        console.warn('Some upload elements not found');
        return;
    }

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);

    // Click to upload functionality
    dropArea.addEventListener('click', function(e) {
        if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'I') {
            fileInput.click();
        }
    });

    // Handle file input change
    fileInput.addEventListener('change', function(e) {
        handleFiles(e.target.files);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropArea.style.borderColor = 'var(--primary-color)';
        dropArea.style.backgroundColor = 'rgba(139, 92, 246, 0.05)';
    }

    function unhighlight() {
        dropArea.style.borderColor = 'var(--border-color)';
        dropArea.style.backgroundColor = 'var(--background-light)';
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            
            // Validate file type
            const allowedTypes = ['application/pdf', 'application/msword', 
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'text/plain'];
            
            const allowedExtensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt'];
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            
            if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
                alert('Please select a valid file type (PDF, Word, PowerPoint, or Text)');
                return;
            }
            
            // Check file size (50MB limit)
            if (file.size > 50 * 1024 * 1024) {
                alert('File size must be less than 50MB');
                return;
            }
            
            showFilePreview(file);
        }
    }

    function showFilePreview(file) {
        const fileIcon = document.getElementById('file-icon');
        const fileName = document.getElementById('file-name');
        const fileSize = document.getElementById('file-size');
        
        if (!fileIcon || !fileName || !fileSize) return;
        
        // Get file extension
        const extension = file.name.split('.').pop().toLowerCase();
        
        // Set icon and color based on file type
        let iconClass = 'fas fa-file';
        let iconColor = '#6b7280';
        
        switch(extension) {
            case 'pdf':
                iconClass = 'fas fa-file-pdf';
                iconColor = '#ef4444';
                break;
            case 'doc':
            case 'docx':
                iconClass = 'fas fa-file-word';
                iconColor = '#3b82f6';
                break;
            case 'ppt':
            case 'pptx':
                iconClass = 'fas fa-file-powerpoint';
                iconColor = '#f59e0b';
                break;
            case 'txt':
                iconClass = 'fas fa-file-alt';
                iconColor = '#10b981';
                break;
        }
        
        fileIcon.innerHTML = `<i class="${iconClass}"></i>`;
        fileIcon.style.background = iconColor;
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        
        filePreview.style.display = 'block';
    }

    window.removeFile = function() {
        fileInput.value = '';
        filePreview.style.display = 'none';
    };

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Form submission
    form.addEventListener('submit', function(e) {
        const startChatBtn = document.getElementById('start-chat-btn');
        const fileInputValue = fileInput.value;
        
        // Check if file is selected
        if (!fileInputValue) {
            e.preventDefault();
            alert('Please select a file to upload');
            return false;
        }
        
        // Show loading state
        const originalText = startChatBtn.innerHTML;
        startChatBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        startChatBtn.disabled = true;
        
        // Re-enable after timeout (failsafe)
        setTimeout(() => {
            startChatBtn.innerHTML = originalText;
            startChatBtn.disabled = false;
        }, 30000);
    });
});