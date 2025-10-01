document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const fileList = document.getElementById('fileList');
    const generateBtn = document.getElementById('generateBtn');
    const slideCountSelect = document.getElementById('slideCount');
    const customSlideCount = document.getElementById('customSlideCount');
    const form = document.getElementById('slideGeneratorForm');
    const progressContainer = document.getElementById('progressContainer');
    const chooseBtn = uploadArea.querySelector('button.btn');
    const initialProgressHTML = progressContainer ? progressContainer.innerHTML : '';
    const bgInput = document.getElementById('bgImage');
    const bgPreviewWrap = document.getElementById('bgPreviewWrap');
    const bgPreview = document.getElementById('bgPreview');
    
    let selectedFiles = [];

    // Handle file input change
    fileInput.addEventListener('change', function(e) {
        handleFiles(e.target.files);
    });

    // Handle drag and drop
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    // Improve UX: clicking the area or button opens the file dialog
    uploadArea.addEventListener('click', function(e) {
        // Avoid double-trigger when the hidden input is clicked
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });
    if (chooseBtn) {
        chooseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            fileInput.click();
        });
    }

    // Handle slide count selection
    slideCountSelect.addEventListener('change', function() {
        if (this.value === 'custom') {
            customSlideCount.style.display = 'block';
        } else {
            customSlideCount.style.display = 'none';
        }
    });

    // Handle files
    function handleFiles(files) {
        const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'];
        
        Array.from(files).forEach(file => {
            if (allowedTypes.includes(file.type) || file.name.toLowerCase().match(/\.(pdf|doc|docx|txt|ppt|pptx)$/)) {
                if (!selectedFiles.find(f => f.name === file.name && f.size === file.size)) {
                    selectedFiles.push(file);
                }
            } else {
                alert(`File type not supported: ${file.name}`);
            }
        });

        updateFilePreview();
        updateGenerateButton();
    }

    // Background image preview
    if (bgInput) {
        bgInput.addEventListener('change', function(e) {
            const file = e.target.files && e.target.files[0];
            if (!file) {
                if (bgPreviewWrap) bgPreviewWrap.style.display = 'none';
                return;
            }
            const reader = new FileReader();
            reader.onload = function(evt) {
                if (bgPreview) bgPreview.src = evt.target.result;
                if (bgPreviewWrap) bgPreviewWrap.style.display = 'block';
            };
            reader.readAsDataURL(file);
        });
    }

    // Update file preview
    function updateFilePreview() {
        if (selectedFiles.length === 0) {
            filePreview.classList.remove('show');
            return;
        }

        fileList.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            const fileExtension = file.name.split('.').pop().toLowerCase();
            let iconClass = 'fas fa-file';
            
            switch(fileExtension) {
                case 'pdf':
                    iconClass = 'fas fa-file-pdf';
                    break;
                case 'doc':
                case 'docx':
                    iconClass = 'fas fa-file-word';
                    break;
                case 'ppt':
                case 'pptx':
                    iconClass = 'fas fa-file-powerpoint';
                    break;
                case 'txt':
                    iconClass = 'fas fa-file-alt';
                    break;
            }

            fileItem.innerHTML = `
                <i class="${iconClass} file-icon"></i>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
                <button type="button" class="remove-file" onclick="removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            fileList.appendChild(fileItem);
        });

        filePreview.classList.add('show');
    }

    // Remove file
    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        updateFilePreview();
        updateGenerateButton();
    };

    // Update generate button state
    function updateGenerateButton() {
        generateBtn.disabled = selectedFiles.length === 0;
    }

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Handle form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (selectedFiles.length === 0) {
            alert('Please select at least one file to generate slides.');
            return;
        }

        // Create FormData
        const formData = new FormData(form);
        
        // Clear existing file input and add selected files
        formData.delete('documents');
        selectedFiles.forEach(file => {
            formData.append('documents', file);
        });
        // background_image is already in the form if selected; no extra handling needed

        // Show progress
        progressContainer.classList.add('show');
        generateBtn.disabled = true;
        
        // Submit to Django backend
        submitSlideGeneration(formData);
    });

    // Submit slide generation to Django backend
    function submitSlideGeneration(formData) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        // Reset progress
        progressBar.style.width = '10%';
        progressText.textContent = 'Uploading files...';
        
        fetch('{% url "rag_app:slide_generate" %}', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                progressBar.style.width = '100%';
                progressText.textContent = 'Presentation generated successfully!';
                
                setTimeout(() => {
                    // Create download section
                    const downloadSection = document.createElement('div');
                    downloadSection.className = 'text-center mt-4 p-4 bg-light rounded';
                    downloadSection.innerHTML = `
                        <div class="mb-3">
                            <i class="fas fa-check-circle text-success" style="font-size: 3rem;"></i>
                        </div>
                        <h4 class="text-success mb-3">Presentation Ready!</h4>
                        <p class="text-muted mb-4">Your PowerPoint presentation has been generated successfully.</p>
                    `;
                    
                    // Create download button
                    const downloadBtn = document.createElement('a');
                    downloadBtn.href = data.download_url;
                    downloadBtn.download = data.file_name;
                    downloadBtn.className = 'btn btn-success btn-lg px-5 py-3';
                    downloadBtn.innerHTML = '<i class="fas fa-download me-2"></i>Download PowerPoint';
                    downloadBtn.style.cssText = 'text-decoration: none; font-weight: 600; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);';
                    
                    // Add hover effect
                    downloadBtn.addEventListener('mouseenter', function() {
                        this.style.transform = 'translateY(-2px)';
                        this.style.boxShadow = '0 6px 20px rgba(40, 167, 69, 0.4)';
                    });
                    downloadBtn.addEventListener('mouseleave', function() {
                        this.style.transform = 'translateY(0)';
                        this.style.boxShadow = '0 4px 15px rgba(40, 167, 69, 0.3)';
                    });
                    
                    downloadSection.appendChild(downloadBtn);
                    
                    // Create new session button
                    const newSessionBtn = document.createElement('button');
                    newSessionBtn.className = 'btn btn-outline-primary btn-lg ms-3 px-4 py-3';
                    newSessionBtn.innerHTML = '<i class="fas fa-plus me-2"></i>Generate Another';
                    newSessionBtn.style.cssText = 'font-weight: 600;';
                    newSessionBtn.addEventListener('click', function() {
                        // Reset UI without full page reload
                        selectedFiles = [];
                        if (fileList) fileList.innerHTML = '';
                        if (filePreview) filePreview.classList.remove('show');
                        if (progressContainer) {
                            progressContainer.classList.remove('show');
                            progressContainer.innerHTML = initialProgressHTML;
                        }
                        if (form) form.reset();
                        updateGenerateButton();
                        // Re-bind references after restoring HTML
                        const newProgressBar = document.getElementById('progressBar');
                        const newProgressText = document.getElementById('progressText');
                        if (newProgressBar) newProgressBar.style.width = '0%';
                        if (newProgressText) newProgressText.textContent = 'Initializing...';
                    });
                    
                    downloadSection.appendChild(newSessionBtn);
                    
                    // Replace progress container content
                    progressContainer.innerHTML = '';
                    progressContainer.appendChild(downloadSection);
                    
                    generateBtn.disabled = false;
                }, 1000);
            } else {
                progressBar.style.width = '0%';
                progressText.textContent = 'Error occurred';
                generateBtn.disabled = false;
                
                // Show error message
                const errorMessage = document.createElement('div');
                errorMessage.className = 'alert alert-danger mt-3';
                errorMessage.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Error: ${data.error}`;
                progressContainer.appendChild(errorMessage);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            progressBar.style.width = '0%';
            progressText.textContent = 'Error occurred';
            generateBtn.disabled = false;
            
            // Show error message
            const errorMessage = document.createElement('div');
            errorMessage.className = 'alert alert-danger mt-3';
            errorMessage.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>An error occurred while generating slides.';
            progressContainer.appendChild(errorMessage);
        });
    }

    // Removed simulated progress to avoid conflicting UI updates during real generation
});