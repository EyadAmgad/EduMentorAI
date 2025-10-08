document.addEventListener('DOMContentLoaded', function() {
    const viewQuestionsBtns = document.querySelectorAll('.view-questions-btn');
    const quizQuestions = document.getElementById('quizQuestions');
    
    // Check if required elements exist
    if (!quizQuestions) {
        console.error('Quiz questions container not found');
        return;
    }
    
    viewQuestionsBtns.forEach(btn => {
        btn.addEventListener('click', async function() {
            const quizId = this.getAttribute('data-quiz-id');
            
            if (!quizId) {
                console.error('Quiz ID not found');
                return;
            }
            
            // Show loading state
            this.disabled = true;
            const originalHTML = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Loading...';
            
            try {
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                                document.querySelector('input[name=csrfmiddlewaretoken]')?.value || '';
                
                const response = await fetch(`/ajax/quizzes/${quizId}/questions/`, {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.success && data.questions && Array.isArray(data.questions)) {
                    // Helper function to escape HTML
                    function escapeHtml(text) {
                        const div = document.createElement('div');
                        div.textContent = text;
                        return div.innerHTML;
                    }
                    
                    // Links section (shown above questions)
                    let linksHTML = '';
                    if (data.google_form_url) {
                        linksHTML += `
                            <div class="mb-3 d-grid gap-2">
                                <a href="${escapeHtml(data.google_form_url)}" target="_blank" rel="noopener" class="btn btn-success">
                                    <i class="fas fa-external-link-alt me-2"></i> Open Google Form
                                </a>
                                ${data.google_form_edit_url ? `
                                <a href="${escapeHtml(data.google_form_edit_url)}" target="_blank" rel="noopener" class="btn btn-outline-primary">
                                    <i class="fas fa-edit me-2"></i> Edit Google Form
                                </a>` : ''}
                            </div>
                        `;
                    }
                    
                    // Generate HTML for questions
                    const questionsHTML = data.questions.map((q, index) => {
                        if (!q.question || !Array.isArray(q.choices)) {
                            console.warn(`Invalid question data at index ${index}:`, q);
                            return '';
                        }
                        
                        return `
                            <div class="question-item">
                                <div class="question-text">${escapeHtml(q.question)}</div>
                                <ul class="choices-list">
                                    ${q.choices.map(c => {
                                        if (!c.text) return '';
                                        return `
                                            <li class="choice-item ${c.is_correct ? 'correct' : ''}">
                                                ${escapeHtml(c.text)}
                                            </li>
                                        `;
                                    }).join('')}
                                </ul>
                                ${q.explanation ? `
                                    <div class="explanation">
                                        <strong>Explanation:</strong> ${escapeHtml(q.explanation)}
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).filter(html => html !== '').join('');
                    
                    // Update modal content: links first, then questions
                    if (quizQuestions) {
                        quizQuestions.innerHTML = linksHTML + questionsHTML;
                    }
                    
                    // Show modal
                    const modal = document.getElementById('quizContentModal');
                    if (modal) {
                        new bootstrap.Modal(modal).show();
                    }
                } else {
                    alert('Error loading questions: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error loading quiz questions:', error);
                alert('Error loading questions. Please try again.');
            } finally {
                // Restore button state
                this.disabled = false;
                this.innerHTML = originalHTML;
            }
        });
    });
});