document.addEventListener('DOMContentLoaded', function() {
    const questionCards = document.querySelectorAll('.question-card');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');
    const progressText = document.getElementById('progressText');
    const progressFill = document.getElementById('progressFill');
    const quizForm = document.getElementById('quizForm');
    
    let currentQuestion = 0;
    const totalQuestions = questionCards.length;
    
    if (totalQuestions === 0) return;

    // Initialize
    updateNavigation();
    updateProgress();

    // Choice selection handlers
    document.querySelectorAll('.choice').forEach(choice => {
        choice.addEventListener('click', function() {
            const input = this.querySelector('input[type="radio"]');
            const questionCard = this.closest('.question-card');
            
            // Remove selected class from all choices in this question
            questionCard.querySelectorAll('.choice').forEach(c => {
                c.classList.remove('selected');
            });
            
            // Add selected class to this choice
            this.classList.add('selected');
            input.checked = true;
            
            // Update navigation
            updateNavigation();
        });
    });

    // Navigation event listeners
    prevBtn.addEventListener('click', () => {
        if (currentQuestion > 0) {
            showQuestion(currentQuestion - 1);
        }
    });

    nextBtn.addEventListener('click', () => {
        if (currentQuestion < totalQuestions - 1) {
            showQuestion(currentQuestion + 1);
        }
    });

    submitBtn.addEventListener('click', (e) => {
        e.preventDefault();
        
        if (confirm('Are you sure you want to submit your quiz? You won\'t be able to change your answers after submission.')) {
            submitQuiz();
        }
    });

    function showQuestion(questionIndex) {
        // Hide current question
        questionCards[currentQuestion].style.display = 'none';
        questionCards[currentQuestion].classList.remove('current');
        
        // Show new question
        currentQuestion = questionIndex;
        questionCards[currentQuestion].style.display = 'block';
        questionCards[currentQuestion].classList.add('current');
        
        // Update navigation and progress
        updateNavigation();
        updateProgress();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function updateNavigation() {
        // Previous button
        prevBtn.disabled = currentQuestion === 0;
        
        // Next/Submit button
        if (currentQuestion === totalQuestions - 1) {
            nextBtn.style.display = 'none';
            submitBtn.style.display = 'flex';
        } else {
            nextBtn.style.display = 'flex';
            submitBtn.style.display = 'none';
        }
        
        // Check if current question is answered
        const currentCard = questionCards[currentQuestion];
        const isAnswered = currentCard.querySelector('input[type="radio"]:checked');
        
        nextBtn.disabled = !isAnswered;
        submitBtn.disabled = !allQuestionsAnswered();
    }

    function updateProgress() {
        const progress = ((currentQuestion + 1) / totalQuestions) * 100;
        progressText.textContent = `${currentQuestion + 1} of ${totalQuestions}`;
        progressFill.style.width = `${progress}%`;
    }

    function allQuestionsAnswered() {
        return Array.from(questionCards).every(card => {
            return card.querySelector('input[type="radio"]:checked');
        });
    }

    function submitQuiz() {
        const formData = new FormData(quizForm);
        
        // Show loading state
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
        submitBtn.disabled = true;
        
        // Submit the form
        fetch(window.location.href, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showResults(data);
            } else {
                alert('Error submitting quiz. Please try again.');
                submitBtn.innerHTML = '<i class="fas fa-check"></i> Submit Quiz';
                submitBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error submitting quiz. Please try again.');
            submitBtn.innerHTML = '<i class="fas fa-check"></i> Submit Quiz';
            submitBtn.disabled = false;
        });
    }

    function showResults(data) {
        // Hide quiz form
        document.getElementById('quizForm').style.display = 'none';
        
        // Show results
        const resultsHTML = `
            <div class="quiz-results">
                <div class="score-circle">
                    ${data.score}%
                </div>
                <h2>Quiz Completed!</h2>
                <p>You scored ${data.correct_answers} out of ${data.total_questions} questions correctly.</p>
                <div class="results-actions">
                    <a href="${data.review_url}" class="nav-button btn-next">
                        <i class="fas fa-eye"></i>
                        Review Answers
                    </a>
                    <a href="{% url 'rag_app:dashboard' %}" class="nav-button btn-previous">
                        <i class="fas fa-home"></i>
                        Back to Dashboard
                    </a>
                </div>
            </div>
        `;
        
        document.querySelector('.quiz-container').innerHTML = resultsHTML;
    }

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowLeft' && !prevBtn.disabled) {
            prevBtn.click();
        } else if (e.key === 'ArrowRight' && !nextBtn.disabled) {
            nextBtn.click();
        } else if (e.key === 'Enter' && currentQuestion === totalQuestions - 1 && !submitBtn.disabled) {
            submitBtn.click();
        }
    });
});