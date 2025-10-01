document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('quizGenerateForm');
    const results = document.getElementById('quizResults');
    const metadata = document.getElementById('quizMetadata');
    const viewQuizButton = document.getElementById('viewQuizButton');
    const googleFormSection = document.getElementById('googleFormSection');
    const googleFormLink = document.getElementById('googleFormLink');
    const googleFormEditLink = document.getElementById('googleFormEditLink');
    const copyFormLinkButton = document.getElementById('copyFormLinkButton');
    const quizQuestions = document.getElementById('quizQuestions');
    
    let currentQuizData = null;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const button = document.getElementById('generateButton');
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';
        
        try {
            const formData = new FormData(form);
            
            // Handle topics
            const topics = formData.get('topics')
                .split(',')
                .map(t => t.trim())
                .filter(t => t);
            if (topics.length) {
                formData.delete('topics');
                topics.forEach(topic => formData.append('topics', topic));
            }
            
            const response = await fetch("{% url 'rag_app:generate_rag_quiz' %}", {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                currentQuizData = data;
                
                // Show metadata
                metadata.innerHTML = `
                    <h6>Quiz Details:</h6>
                    <ul class="list-unstyled">
                        <li><strong>Subject:</strong> ${data.metadata.subject}</li>
                        <li><strong>Questions:</strong> ${data.metadata.num_questions}</li>
                        <li><strong>Topics:</strong> ${data.metadata.topics.join(', ')}</li>
                        <li><strong>Sources:</strong> ${data.metadata.sources.length} documents</li>
                    </ul>
                `;
                
                // Show Google Form link if available
                if (data.google_form_url) {
                    if (googleFormLink) {
                        googleFormLink.href = data.google_form_url;
                    }
                    
                    // Show edit link if available
                    const editLink = document.getElementById('googleFormEditLink');
                    if (data.google_form_edit_url && editLink) {
                        editLink.href = data.google_form_edit_url;
                        editLink.style.display = 'block';
                    }
                    
                    // Display form details
                    const formDetails = document.getElementById('formDetails');
                    if (formDetails) {
                        let detailsHTML = `
                            <p class=\"mb-2\"><strong>Form URL:</strong><br>
                            <small class=\"text-muted font-monospace\">${data.google_form_url}</small></p>
                        `;
                        
                        if (data.google_form_edit_url) {
                            detailsHTML += `
                                <p class=\"mb-2\"><strong>Edit URL:</strong><br>
                                <small class=\"text-muted font-monospace\">${data.google_form_edit_url}</small></p>
                            `;
                        }
                        
                        if (data.ownership_transfer && data.ownership_transfer.status === 'success') {
                            detailsHTML += `
                                <p class=\"mb-0\"><strong>Ownership Transfer:</strong><br>
                                <small class=\"text-success\">✅ Invitation sent to: ${data.ownership_transfer.new_owner}</small></p>
                            `;
                        } else {
                            detailsHTML += `
                                <p class=\"mb-0\"><strong>Ownership:</strong><br>
                                <small class=\"text-warning\">Ownership transfer may have failed or was not requested.</small></p>
                            `;
                        }
                        
                        formDetails.innerHTML = detailsHTML;
                    }
                    if (googleFormSection) {
                        googleFormSection.style.display = 'block';
                    }
                } else {
                    if (googleFormSection) {
                        googleFormSection.style.display = 'none';
                    }
                }
                
                // Show results
                results.style.display = 'block';
                results.scrollIntoView({ behavior: 'smooth' });

                // Offer link to open saved quiz if persisted
                const savedStatus = document.createElement('div');
                savedStatus.className = 'mt-3';
                if (data.quiz_saved && data.quiz_id) {
                    savedStatus.innerHTML = `
                        <div class="alert alert-success">
                            <i class="fas fa-check-circle me-2"></i>
                            Quiz saved. <a class="fw-semibold" href="/quizzes/${data.quiz_id}/">Open saved quiz</a>
                        </div>`;
                } else {
                    savedStatus.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Quiz not saved to your account yet${data.save_error ? `: <span class="text-muted">${data.save_error}</span>` : ''}.
                        </div>`;
                }
                results.querySelector('.card-body').prepend(savedStatus);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            alert('Error generating quiz: ' + error.message);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-magic me-2"></i> Generate Quiz';
        }
    });
    
    // Handle View Quiz button click
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
        quizQuestions.innerHTML = linksHTML + questionsHTML;
        
        // Show modal
        new bootstrap.Modal(document.getElementById('quizContentModal')).show();
    });

    // Copy Google Form link functionality
    copyFormLinkButton.addEventListener('click', function() {
        if (currentQuizData && currentQuizData.google_form_url) {
            navigator.clipboard.writeText(currentQuizData.google_form_url).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check me-2"></i> Copied!';
                this.classList.remove('btn-outline-success');
                this.classList.add('btn-success');
                
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.classList.remove('btn-success');
                    this.classList.add('btn-outline-success');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
                alert('Failed to copy link to clipboard');
            });
        }
    });
});