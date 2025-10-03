document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('quizGenerateForm');
    const viewQuizButton = document.getElementById('viewQuizButton');
    const viewQuizLinkButton = document.getElementById('viewQuizLinkButton');
    const editQuizLinkButton = document.getElementById('editQuizLinkButton');
    const quizQuestions = document.getElementById('quizQuestions');
    
    let currentQuizData = null;
    
    // Function to display error messages on the page
    function showErrorMessage(message, container = document.body) {
        // Remove any existing error messages
        const existingErrors = document.querySelectorAll('.quiz-error-message');
        existingErrors.forEach(error => error.remove());
        
        // Create error message element
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger quiz-error-message';
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            max-width: 500px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
            animation: slideInDown 0.3s ease-out;
        `;
        
        errorDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close ms-auto" aria-label="Close"></button>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(errorDiv);
        
        // Add close functionality
        const closeBtn = errorDiv.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            errorDiv.remove();
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }
    
    // Function to display inline error messages in specific containers
    function showInlineError(message, container) {
        if (!container) return;
        
        // Remove existing inline errors in this container
        const existingErrors = container.querySelectorAll('.quiz-inline-error');
        existingErrors.forEach(error => error.remove());
        
        // Create inline error element
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger quiz-inline-error mt-3';
        errorDiv.innerHTML = `
            <div class="d-flex align-items-start">
                <i class="fas fa-exclamation-circle me-2 mt-1"></i>
                <div class="flex-grow-1">${message}</div>
                <button type="button" class="btn-close btn-close-sm" aria-label="Close"></button>
            </div>
        `;
        
        // Add close functionality
        const closeBtn = errorDiv.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            errorDiv.remove();
        });
        
        // Add to container
        container.appendChild(errorDiv);
    }
    
    // Function to display success messages
    function showSuccessMessage(message) {
        // Remove any existing success messages
        const existingSuccess = document.querySelectorAll('.quiz-success-message');
        existingSuccess.forEach(success => success.remove());
        
        // Create success message element
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success quiz-success-message';
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            max-width: 500px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
            animation: slideInDown 0.3s ease-out;
        `;
        
        successDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-check-circle me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close ms-auto" aria-label="Close"></button>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(successDiv);
        
        // Add close functionality
        const closeBtn = successDiv.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            successDiv.remove();
        });
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.remove();
            }
        }, 3000);
    }
    
    // Initialize page state
    function initializePage() {
        // Ensure action buttons are hidden on page load
        if (viewQuizLinkButton) {
            viewQuizLinkButton.style.display = 'none';
        }
        if (editQuizLinkButton) {
            editQuizLinkButton.style.display = 'none';
        }
        
        // Ensure Generated Questions button is initially hidden
        if (viewQuizButton) {
            viewQuizButton.style.display = 'none';
        }
    }
    
    // Helper function to reset UI state
    function resetUIState() {
        // Clear any error messages from the page
        const existingErrors = document.querySelectorAll('.quiz-error-message, .quiz-inline-error');
        existingErrors.forEach(error => error.remove());
        
        // Hide action buttons
        if (viewQuizLinkButton) {
            viewQuizLinkButton.style.display = 'none';
            viewQuizLinkButton.href = '#';
        }
        if (editQuizLinkButton) {
            editQuizLinkButton.style.display = 'none';
            editQuizLinkButton.href = '#';
        }
        
        // Hide Generated Questions button
        if (viewQuizButton) {
            viewQuizButton.style.display = 'none';
        }
        
        // Clear quiz questions
        if (quizQuestions) {
            quizQuestions.innerHTML = '';
        }
        
        // Reset current quiz data
        currentQuizData = null;
    }
    
    // Call initialization
    initializePage();
    
    // Form submission handler
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const button = document.getElementById('generateButton');
            if (!button) return;
            
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';
            
            // Reset UI state before starting
            resetUIState();
            
            try {
                const formData = new FormData(form);
                
                // Handle topics
                const topicsInput = formData.get('topics');
                if (topicsInput) {
                    const topics = topicsInput
                        .split(',')
                        .map(t => t.trim())
                        .filter(t => t);
                    if (topics.length) {
                        formData.delete('topics');
                        topics.forEach(topic => formData.append('topics', topic));
                    }
                }
                
                const response = await fetch(window.location.pathname, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    currentQuizData = data;
                    
                    // Show Generated Questions button
                    if (viewQuizButton) {
                        viewQuizButton.style.display = 'block';
                    }
                    
                    // Show Google Form links if available
                    if (data.google_form_url) {
                        // Update view button
                        if (viewQuizLinkButton) {
                            viewQuizLinkButton.href = data.google_form_url;
                            viewQuizLinkButton.style.display = 'block';
                        }
                        
                        // Update edit button if edit URL is available
                        if (data.google_form_edit_url && editQuizLinkButton) {
                            editQuizLinkButton.href = data.google_form_edit_url;
                            editQuizLinkButton.style.display = 'block';
                        }
                    }
                    
                    // Show success message
                    showSuccessMessage('Quiz generated successfully!');
                    
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                console.error('Error generating quiz:', error);
                
                // Show error message on page instead of alert
                const errorContainer = form.parentNode;
                showInlineError(`Error generating quiz: ${error.message}`, errorContainer);
            } finally {
                const button = document.getElementById('generateButton');
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-magic me-2"></i> Generate Quiz';
                }
            }
        });
    }
    
    // Handle View Quiz button click
    if (viewQuizButton) {
        viewQuizButton.addEventListener('click', function() {
            if (!currentQuizData || !currentQuizData.questions) return;
            
            // Links section (shown above questions)
            let linksHTML = '';
            if (currentQuizData.google_form_url) {
                linksHTML += `
                    <div class="mb-3 d-grid gap-2">
                        <a href="${currentQuizData.google_form_url}" target="_blank" class="btn btn-success">
                            <i class="fas fa-external-link-alt me-2"></i> Open Google Form
                        </a>
                        ${currentQuizData.google_form_edit_url ? `
                        <a href="${currentQuizData.google_form_edit_url}" target="_blank" class="btn btn-outline-primary">
                            <i class="fas fa-edit me-2"></i> Edit Google Form
                        </a>` : ''}
                    </div>
                `;
            }
            
            // Generate HTML for questions
            const questionsHTML = currentQuizData.questions.map(q => `
                <div class="question-item">
                    <div class="question-text">${q.question}</div>
                    <ul class="choices-list">
                        ${q.choices.map(c => `
                            <li class="choice-item ${c.is_correct ? 'correct' : ''}">
                                ${c.text}
                                ${c.is_correct ? ' <i class="fas fa-check text-success"></i>' : ''}
                            </li>
                        `).join('')}
                    </ul>
                    <div class="explanation">
                        <strong>Explanation:</strong> ${q.explanation}
                    </div>
                </div>
            `).join('');
            
            // Update modal content: links first, then questions
            if (quizQuestions) {
                quizQuestions.innerHTML = linksHTML + questionsHTML;
            }
            
            // Show modal
            const modal = document.getElementById('quizContentModal');
            if (modal) {
                new bootstrap.Modal(modal).show();
            }
        });
    }
});
