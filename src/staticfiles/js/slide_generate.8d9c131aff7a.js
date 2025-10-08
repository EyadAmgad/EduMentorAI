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
    
    // Content source elements
    const contentSourceOptions = document.querySelectorAll('input[name="content_source"]');
    const documentSelection = document.getElementById('documentSelection');
    const subjectSelection = document.getElementById('subjectSelection');
    const documentCheckboxes = document.querySelectorAll('input[name="selected_documents"]');
    const subjectRadios = document.querySelectorAll('input[name="selected_subject"]');
    
    let selectedFiles = [];

    // Handle content source selection
    contentSourceOptions.forEach(option => {
        option.addEventListener('change', function() {
            const selectedSource = this.value;
            
            // Hide all content sections
            uploadArea.style.display = 'none';
            if (documentSelection) documentSelection.style.display = 'none';
            if (subjectSelection) subjectSelection.style.display = 'none';
            
            // Show the relevant section
            if (selectedSource === 'upload') {
                uploadArea.style.display = 'block';
                // Don't hide file preview or clear files if they exist
                // Let the user keep their uploaded files when switching modes
            } else if (selectedSource === 'existing_documents' && documentSelection) {
                documentSelection.style.display = 'block';
            } else if (selectedSource === 'subject' && subjectSelection) {
                subjectSelection.style.display = 'block';
            }
            
            // Always update the button state after changing source
            setTimeout(updateGenerateButton, 100);
        });
    });
    
    // Handle document selection
    if (documentCheckboxes) {
        documentCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateGenerateButton);
        });
    }
    
    // Handle subject selection
    if (subjectRadios) {
        subjectRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                updateGenerateButton();
                // Auto-update title when subject is selected
                const titleInput = document.getElementById('presentationTitle');
                if (titleInput && !titleInput.value.trim()) {
                    const selectedLabel = document.querySelector(`label[for="${this.id}"]`);
                    if (selectedLabel) {
                        const subjectTitle = selectedLabel.querySelector('.subject-title');
                        if (subjectTitle) {
                            titleInput.value = subjectTitle.textContent.trim() + ' - Presentation';
                        }
                    }
                }
            });
        });
    }

    // Handle file input change
    fileInput.addEventListener('change', function(e) {
        console.log('File input changed', e.target.files);
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
        console.log('Upload area clicked', e.target);
        // Avoid double-trigger when the hidden input is clicked
        if (e.target !== fileInput) {
            console.log('Triggering file input click');
            fileInput.click();
        }
    });
    if (chooseBtn) {
        chooseBtn.addEventListener('click', function(e) {
            console.log('Choose button clicked');
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
        console.log('HandleFiles called with:', files);
        const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'];
        
        Array.from(files).forEach(file => {
            console.log('Processing file:', file.name, file.type);
            if (allowedTypes.includes(file.type) || file.name.toLowerCase().match(/\.(pdf|doc|docx|txt|ppt|pptx)$/)) {
                if (!selectedFiles.find(f => f.name === file.name && f.size === file.size)) {
                    selectedFiles.push(file);
                    console.log('File added:', file.name);
                } else {
                    console.log('File already exists:', file.name);
                }
            } else {
                console.log('File type not supported:', file.name, file.type);
                alert(`File type not supported: ${file.name}`);
            }
        });

        console.log('Selected files:', selectedFiles);
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
        console.log('updateFilePreview called', {
            filePreview: filePreview,
            fileList: fileList,
            selectedFilesLength: selectedFiles.length
        });
        
        if (selectedFiles.length === 0) {
            if (filePreview) filePreview.classList.remove('show');
            return;
        }

        if (!fileList) {
            console.error('fileList element not found');
            return;
        }

        fileList.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            console.log('Adding file to preview:', file.name);
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

        if (filePreview) {
            filePreview.classList.add('show');
            console.log('File preview should now be visible');
        } else {
            console.error('filePreview element not found');
        }
    }

    // Remove file
    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        updateFilePreview();
        updateGenerateButton();
    };

    // Update generate button state
    function updateGenerateButton() {
        if (!generateBtn) return;
        
        const selectedSourceElement = document.querySelector('input[name="content_source"]:checked');
        if (!selectedSourceElement) {
            generateBtn.disabled = true;
            return;
        }
        
        const selectedSource = selectedSourceElement.value;
        let hasContent = false;
        
        if (selectedSource === 'upload') {
            hasContent = selectedFiles.length > 0;
        } else if (selectedSource === 'existing_documents') {
            const selectedDocs = document.querySelectorAll('input[name="selected_documents"]:checked');
            hasContent = selectedDocs.length > 0;
        } else if (selectedSource === 'subject') {
            const selectedSubject = document.querySelector('input[name="selected_subject"]:checked');
            hasContent = selectedSubject !== null;
        }
        
        // Debug logging
        console.log('UpdateGenerateButton:', {
            selectedSource,
            hasContent,
            filesCount: selectedFiles.length,
            selectedDocsCount: document.querySelectorAll('input[name="selected_documents"]:checked').length,
            selectedSubject: document.querySelector('input[name="selected_subject"]:checked')
        });
        
        generateBtn.disabled = !hasContent;
        
        // Add visual feedback
        if (hasContent) {
            generateBtn.classList.remove('btn-secondary');
            generateBtn.classList.add('generate-btn');
        } else {
            generateBtn.classList.remove('generate-btn');
            generateBtn.classList.add('btn-secondary');
        }
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
        
        const selectedSource = document.querySelector('input[name="content_source"]:checked').value;
        let hasContent = false;
        let errorMessage = '';
        
        if (selectedSource === 'upload') {
            hasContent = selectedFiles.length > 0;
            errorMessage = 'Please select at least one file to generate slides.';
        } else if (selectedSource === 'existing_documents') {
            const selectedDocs = document.querySelectorAll('input[name="selected_documents"]:checked');
            hasContent = selectedDocs.length > 0;
            errorMessage = 'Please select at least one document to generate slides.';
        } else if (selectedSource === 'subject') {
            const selectedSubject = document.querySelector('input[name="selected_subject"]:checked');
            hasContent = selectedSubject !== null;
            errorMessage = 'Please select a subject to generate slides.';
        }
        
        if (!hasContent) {
            alert(errorMessage);
            return;
        }

        // Create FormData
        const formData = new FormData(form);
        
        // For upload option, handle files specially
        if (selectedSource === 'upload') {
            // Clear existing file input and add selected files
            formData.delete('documents');
            selectedFiles.forEach(file => {
                formData.append('documents', file);
            });
        }
        // For other options, the form data is already handled by the form inputs
        
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
        
        fetch('/slides/generate/', {
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

    // Initialize the page state
    function initializePage() {
        console.log('Initializing page...', {
            uploadArea: uploadArea,
            filePreview: filePreview,
            fileList: fileList,
            generateBtn: generateBtn
        });
        
        // Set initial visibility based on default selection
        const selectedSource = document.querySelector('input[name="content_source"]:checked');
        if (selectedSource) {
            const sourceValue = selectedSource.value;
            console.log('Default content source:', sourceValue);
            
            // Hide all sections first
            if (documentSelection) documentSelection.style.display = 'none';
            if (subjectSelection) subjectSelection.style.display = 'none';
            uploadArea.style.display = 'none';
            
            // Show the correct section
            if (sourceValue === 'upload') {
                uploadArea.style.display = 'block';
                console.log('Upload area should be visible');
            } else if (sourceValue === 'existing_documents' && documentSelection) {
                documentSelection.style.display = 'block';
            } else if (sourceValue === 'subject' && subjectSelection) {
                subjectSelection.style.display = 'block';
            }
        }
        
        // Initialize button state
        updateGenerateButton();
    }

    // Initialize the page state on load
    initializePage();
    
    // Test function for debugging
    window.testFilePreview = function() {
        console.log('Testing file preview...');
        if (selectedFiles.length === 0) {
            // Add a dummy file for testing
            selectedFiles.push({
                name: 'test.pdf',
                size: 1234567,
                type: 'application/pdf'
            });
        }
        updateFilePreview();
    };
    
    // Removed simulated progress to avoid conflicting UI updates during real generation
});