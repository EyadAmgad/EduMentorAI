// EduMentorAI Main JavaScript
(function() {
    'use strict';

    // Utility functions
    const Utils = {
        // Show loading overlay
        showLoading: function(message = 'Processing...') {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.querySelector('.loading-spinner div:last-child').textContent = message;
                overlay.style.display = 'flex';
            }
        },

        // Hide loading overlay
        hideLoading: function() {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
        },

        // Show toast notification
        showToast: function(message, type = 'success') {
            const toastContainer = this.getOrCreateToastContainer();
            const toast = this.createToast(message, type);
            toastContainer.appendChild(toast);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                toast.remove();
            }, 5000);
        },

        // Get or create toast container
        getOrCreateToastContainer: function() {
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.className = 'toast-container position-fixed top-0 end-0 p-3';
                container.style.zIndex = '9999';
                document.body.appendChild(container);
            }
            return container;
        },

        // Create toast element
        createToast: function(message, type) {
            const icons = {
                success: 'fas fa-check-circle',
                error: 'fas fa-exclamation-circle',
                warning: 'fas fa-exclamation-triangle',
                info: 'fas fa-info-circle'
            };

            const toast = document.createElement('div');
            toast.className = `toast show bg-${type === 'error' ? 'danger' : type} text-white`;
            toast.innerHTML = `
                <div class="toast-body d-flex align-items-center">
                    <i class="${icons[type] || icons.info} me-2"></i>
                    ${message}
                    <button type="button" class="btn-close btn-close-white ms-auto" onclick="this.closest('.toast').remove()"></button>
                </div>
            `;
            return toast;
        },

        // Format file size
        formatFileSize: function(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        // Format date
        formatDate: function(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        // AJAX helper
        ajax: function(url, options = {}) {
            const defaults = {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            };
            
            const config = { ...defaults, ...options };
            
            return fetch(url, config)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .catch(error => {
                    console.error('AJAX Error:', error);
                    throw error;
                });
        }
    };

    // Chat functionality
    const Chat = {
        init: function() {
            this.bindEvents();
            this.scrollToBottom();
        },

        bindEvents: function() {
            const chatForm = document.getElementById('chat-form');
            const messageInput = document.getElementById('message-input');
            const sendButton = document.getElementById('send-button');

            if (chatForm) {
                chatForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.sendMessage();
                });
            }

            if (messageInput) {
                messageInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this.sendMessage();
                    }
                });

                messageInput.addEventListener('input', () => {
                    this.adjustTextareaHeight(messageInput);
                });
            }
        },

        sendMessage: function() {
            const messageInput = document.getElementById('message-input');
            const message = messageInput.value.trim();
            
            if (!message) return;

            const sessionId = document.querySelector('[data-session-id]')?.dataset.sessionId;
            const subjectId = document.querySelector('[data-subject-id]')?.dataset.subjectId;

            // Disable input while sending
            messageInput.disabled = true;
            document.getElementById('send-button').disabled = true;

            // Add user message to chat
            this.addMessage(message, true);
            messageInput.value = '';
            this.adjustTextareaHeight(messageInput);

            // Send AJAX request
            Utils.ajax('/chat/ajax/send/', {
                method: 'POST',
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId,
                    subject_id: subjectId
                })
            })
            .then(data => {
                if (data.success) {
                    this.addMessage(data.ai_message.message, false);
                    // Update session ID if new session
                    if (data.session_id && !sessionId) {
                        const sessionElement = document.querySelector('[data-session-id]');
                        if (sessionElement) {
                            sessionElement.dataset.sessionId = data.session_id;
                        }
                    }
                } else {
                    Utils.showToast('Error sending message', 'error');
                }
            })
            .catch(error => {
                console.error('Chat error:', error);
                Utils.showToast('Error sending message', 'error');
            })
            .finally(() => {
                messageInput.disabled = false;
                document.getElementById('send-button').disabled = false;
                messageInput.focus();
            });
        },

        addMessage: function(message, isUser) {
            const messagesContainer = document.getElementById('chat-messages');
            if (!messagesContainer) return;

            const messageElement = document.createElement('div');
            messageElement.className = `message ${isUser ? 'user' : 'ai'} fade-in`;
            
            const avatar = isUser ? 
                (document.querySelector('.user-avatar img')?.src || 'U') : 
                'AI';
            
            messageElement.innerHTML = `
                <div class="message-avatar">
                    ${avatar.length === 1 ? avatar : `<img src="${avatar}" alt="Avatar" class="rounded-circle" width="40" height="40">`}
                </div>
                <div class="message-content">
                    <div class="message-text">${this.formatMessage(message)}</div>
                    <div class="message-time">${new Date().toLocaleTimeString()}</div>
                </div>
            `;

            messagesContainer.appendChild(messageElement);
            this.scrollToBottom();
        },

        formatMessage: function(message) {
            // Convert newlines to <br> and format basic markdown
            return message
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>');
        },

        adjustTextareaHeight: function(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        },

        scrollToBottom: function() {
            const messagesContainer = document.getElementById('chat-messages');
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
    };

    // File upload functionality
    const FileUpload = {
        init: function() {
            this.bindEvents();
        },

        bindEvents: function() {
            // File input change
            const fileInputs = document.querySelectorAll('input[type="file"]');
            fileInputs.forEach(input => {
                input.addEventListener('change', (e) => {
                    this.handleFileSelect(e);
                });
            });

            // Drag and drop
            const dropzones = document.querySelectorAll('.dropzone');
            dropzones.forEach(zone => {
                zone.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    zone.classList.add('dragover');
                });

                zone.addEventListener('dragleave', () => {
                    zone.classList.remove('dragover');
                });

                zone.addEventListener('drop', (e) => {
                    e.preventDefault();
                    zone.classList.remove('dragover');
                    this.handleFileDrop(e, zone);
                });

                zone.addEventListener('click', () => {
                    const fileInput = zone.querySelector('input[type="file"]');
                    if (fileInput) {
                        fileInput.click();
                    }
                });
            });
        },

        handleFileSelect: function(event) {
            const files = event.target.files;
            this.processFiles(files, event.target.closest('.dropzone'));
        },

        handleFileDrop: function(event, dropzone) {
            const files = event.dataTransfer.files;
            const fileInput = dropzone.querySelector('input[type="file"]');
            if (fileInput) {
                fileInput.files = files;
            }
            this.processFiles(files, dropzone);
        },

        processFiles: function(files, dropzone) {
            if (!files.length) return;

            const fileList = dropzone.querySelector('.file-list');
            if (fileList) {
                fileList.innerHTML = '';

                Array.from(files).forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item d-flex align-items-center justify-content-between p-2 border rounded mb-2';
                    fileItem.innerHTML = `
                        <div class="d-flex align-items-center">
                            <i class="fas fa-file me-2"></i>
                            <div>
                                <div class="fw-medium">${file.name}</div>
                                <small class="text-muted">${Utils.formatFileSize(file.size)}</small>
                            </div>
                        </div>
                        <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.file-item').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    `;
                    fileList.appendChild(fileItem);
                });
            }
        }
    };

    // Quiz functionality
    const Quiz = {
        init: function() {
            this.bindEvents();
            this.initTimer();
        },

        bindEvents: function() {
            // Quiz submission
            const quizForm = document.getElementById('quiz-form');
            if (quizForm) {
                quizForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.submitQuiz();
                });
            }

            // Auto-save answers
            const answerInputs = document.querySelectorAll('.quiz-question input, .quiz-question textarea');
            answerInputs.forEach(input => {
                input.addEventListener('change', () => {
                    this.autoSaveAnswer(input);
                });
            });
        },

        initTimer: function() {
            const timerElement = document.getElementById('quiz-timer');
            if (!timerElement) return;

            const timeLimit = parseInt(timerElement.dataset.timeLimit) * 60; // Convert to seconds
            let timeLeft = timeLimit;

            const timer = setInterval(() => {
                timeLeft--;
                
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                
                timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                
                // Warning when 5 minutes left
                if (timeLeft === 300) {
                    Utils.showToast('5 minutes remaining!', 'warning');
                }
                
                // Warning when 1 minute left
                if (timeLeft === 60) {
                    Utils.showToast('1 minute remaining!', 'warning');
                    timerElement.classList.add('text-danger');
                }
                
                // Time's up
                if (timeLeft <= 0) {
                    clearInterval(timer);
                    Utils.showToast('Time\'s up! Submitting quiz...', 'warning');
                    this.submitQuiz();
                }
            }, 1000);
        },

        submitQuiz: function() {
            const form = document.getElementById('quiz-form');
            if (!form) return;

            Utils.showLoading('Submitting quiz...');
            
            // Disable all inputs
            const inputs = form.querySelectorAll('input, textarea, button');
            inputs.forEach(input => input.disabled = true);

            // Submit form
            form.submit();
        },

        autoSaveAnswer: function(input) {
            // Auto-save functionality (can be enhanced with AJAX)
            const questionId = input.name;
            const value = input.value;
            
            // Save to localStorage as backup
            localStorage.setItem(`quiz_answer_${questionId}`, value);
        }
    };

    // Search functionality
    const Search = {
        init: function() {
            this.bindEvents();
        },

        bindEvents: function() {
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                let searchTimeout;
                
                searchInput.addEventListener('input', (e) => {
                    clearTimeout(searchTimeout);
                    searchTimeout = setTimeout(() => {
                        this.performSearch(e.target.value);
                    }, 300);
                });
            }
        },

        performSearch: function(query) {
            if (query.length < 2) {
                this.clearResults();
                return;
            }

            Utils.showLoading('Searching...');

            Utils.ajax(`/api/search/?q=${encodeURIComponent(query)}`)
                .then(data => {
                    this.displayResults(data.results);
                })
                .catch(error => {
                    console.error('Search error:', error);
                    Utils.showToast('Search failed', 'error');
                })
                .finally(() => {
                    Utils.hideLoading();
                });
        },

        displayResults: function(results) {
            const resultsContainer = document.getElementById('search-results');
            if (!resultsContainer) return;

            if (results.length === 0) {
                resultsContainer.innerHTML = '<div class="text-center text-muted py-4">No results found</div>';
                return;
            }

            resultsContainer.innerHTML = results.map(result => `
                <div class="search-result-item p-3 border-bottom">
                    <h6 class="mb-1">
                        <a href="${result.url}" class="text-decoration-none">${result.title}</a>
                    </h6>
                    <p class="text-muted small mb-1">${result.excerpt}</p>
                    <small class="text-muted">${result.type} • ${Utils.formatDate(result.created_at)}</small>
                </div>
            `).join('');
        },

        clearResults: function() {
            const resultsContainer = document.getElementById('search-results');
            if (resultsContainer) {
                resultsContainer.innerHTML = '';
            }
        }
    };

    // Form validation
    const FormValidation = {
        init: function() {
            this.bindEvents();
        },

        bindEvents: function() {
            const forms = document.querySelectorAll('form[data-validate]');
            forms.forEach(form => {
                form.addEventListener('submit', (e) => {
                    if (!this.validateForm(form)) {
                        e.preventDefault();
                    }
                });
            });
        },

        validateForm: function(form) {
            let isValid = true;
            const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
            
            inputs.forEach(input => {
                if (!this.validateField(input)) {
                    isValid = false;
                }
            });

            return isValid;
        },

        validateField: function(field) {
            const value = field.value.trim();
            let isValid = true;
            let message = '';

            // Required validation
            if (field.hasAttribute('required') && !value) {
                isValid = false;
                message = 'This field is required';
            }

            // Email validation
            if (field.type === 'email' && value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(value)) {
                    isValid = false;
                    message = 'Please enter a valid email address';
                }
            }

            // File validation
            if (field.type === 'file' && field.files.length > 0) {
                const file = field.files[0];
                const maxSize = 10 * 1024 * 1024; // 10MB
                const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
                
                if (file.size > maxSize) {
                    isValid = false;
                    message = 'File size must be less than 10MB';
                } else if (!allowedTypes.includes(file.type)) {
                    isValid = false;
                    message = 'File type not supported';
                }
            }

            this.showFieldValidation(field, isValid, message);
            return isValid;
        },

        showFieldValidation: function(field, isValid, message) {
            const feedbackElement = field.parentNode.querySelector('.invalid-feedback');
            
            if (isValid) {
                field.classList.remove('is-invalid');
                field.classList.add('is-valid');
                if (feedbackElement) {
                    feedbackElement.style.display = 'none';
                }
            } else {
                field.classList.remove('is-valid');
                field.classList.add('is-invalid');
                if (feedbackElement) {
                    feedbackElement.textContent = message;
                    feedbackElement.style.display = 'block';
                }
            }
        }
    };

    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        // Initialize all modules
        Chat.init();
        FileUpload.init();
        Quiz.init();
        Search.init();
        FormValidation.init();

        // Add fade-in animation to page content
        const content = document.querySelector('.main-content');
        if (content) {
            content.classList.add('fade-in');
        }

        // Auto-hide alerts after 5 seconds
        setTimeout(() => {
            const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
            alerts.forEach(alert => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);
    });

    // Make Utils available globally
    window.EduMentorAI = {
        Utils: Utils,
        Chat: Chat,
        FileUpload: FileUpload,
        Quiz: Quiz,
        Search: Search
    };

})();
