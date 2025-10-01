document.addEventListener('DOMContentLoaded', function() {
    // Configure marked for safe rendering
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false
    });

    // DOM Elements
    const chatInput = document.getElementById('chatInput');
    const chatForm = document.getElementById('chatForm');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const chatSidebar = document.getElementById('chatSidebar');
    const mobileOverlay = document.getElementById('mobileOverlay');

    // State
    let currentSessionId = {{ current_session.id|default:"null" }};
    let isLoading = false;

    // Initialize
    setupEventListeners();
    scrollToBottom();

    function setupEventListeners() {
        // Auto-resize textarea
        chatInput.addEventListener('input', handleInputChange);

        // Handle Ctrl+Enter to send message
        chatInput.addEventListener('keydown', handleKeyDown);

        // Form submission
        chatForm.addEventListener('submit', handleFormSubmit);

        // Mobile menu
        mobileMenuBtn.addEventListener('click', toggleMobileMenu);
        mobileOverlay.addEventListener('click', closeMobileMenu);
    }

    function handleInputChange() {
        // Auto-resize
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';

        // Update send button state
        const hasContent = this.value.trim().length > 0;
        sendBtn.disabled = !hasContent;
    }

    function handleKeyDown(e) {
        // Ctrl+Enter or Cmd+Enter to send
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (!isLoading && chatInput.value.trim()) {
                chatForm.requestSubmit();
            }
        }
    }

    function handleFormSubmit(e) {
        e.preventDefault();

        const message = chatInput.value.trim();
        if (!message || isLoading) return;

        // Update UI state
        setLoadingState(true);

        // Add user message
        addMessage('user', message);

        // Clear input
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendBtn.disabled = true;

        // Show typing indicator
        showTypingIndicator();

        // Send to server
        sendMessage(message);
    }

    function sendMessage(message) {
        const url = currentSessionId
            ? `/chat/${currentSessionId}/`
            : '{% url "rag_app:chat" %}';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
            body: new URLSearchParams({ 'message': message })
        })
        .then(response => response.json())
        .then(data => {
            hideTypingIndicator();

            if (data.success) {
                addMessage('ai', data.response);

                // Update session if new
                if (data.session_id && !currentSessionId) {
                    currentSessionId = data.session_id;
                    updateChatTitle(data.session_title || 'AI Chat');
                    window.history.replaceState({}, '', `/chat/${data.session_id}/`);
                }
            } else {
                addMessage('ai', data.error || 'Sorry, something went wrong. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            hideTypingIndicator();
            addMessage('ai', 'Sorry, something went wrong. Please try again.');
        })
        .finally(() => {
            setLoadingState(false);
            chatInput.focus();
        });
    }

    function addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        if (role === 'user') {
            avatar.textContent = '{{ request.user.username|first|upper }}';
        } else {
            avatar.innerHTML = '<i class="fas fa-robot"></i>';
        }

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        if (role === 'user') {
            messageContent.textContent = content;
        } else {
            messageContent.innerHTML = marked.parse(content);
        }

        // Add actions
        const messageActions = document.createElement('div');
        messageActions.className = 'message-actions';
        messageActions.innerHTML = `
            <button class="message-action-btn" onclick="copyMessage(this)" title="Copy message">
                <i class="fas fa-copy"></i>
            </button>
        `;
        messageContent.appendChild(messageActions);

        // Add timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        messageContent.appendChild(timeDiv);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typingIndicator';

        typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="typing-content">
                <span class="typing-text">AI is thinking</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;

        chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    function setLoadingState(loading) {
        isLoading = loading;
        sendBtn.disabled = loading || !chatInput.value.trim();
        chatInput.disabled = loading;
    }

    function scrollToBottom() {
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);
    }

    function toggleMobileMenu() {
        chatSidebar.classList.toggle('show');
        mobileOverlay.classList.toggle('show');
    }

    function closeMobileMenu() {
        chatSidebar.classList.remove('show');
        mobileOverlay.classList.remove('show');
    }

    function updateChatTitle(title) {
        document.getElementById('chatTitle').textContent = title;
    }
});

// Global functions for onclick handlers
function startNewChat() {
    window.location.href = '{% url "rag_app:chat" %}';
}

function loadChatSession(sessionId) {
    window.location.href = `/chat/${sessionId}/`;
}

function useSuggestedPrompt(prompt) {
    const input = document.getElementById('chatInput');
    input.value = prompt;
    input.focus();
    input.dispatchEvent(new Event('input'));
}

function copyMessage(button) {
    const messageContent = button.closest('.message-content');
    const textToCopy = messageContent.textContent.replace(/Copy message/, '').trim();

    navigator.clipboard.writeText(textToCopy).then(() => {
        // Visual feedback
        const originalIcon = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i>';
        button.style.background = '#10b981';
        button.style.color = 'white';

        setTimeout(() => {
            button.innerHTML = originalIcon;
            button.style.background = '';
            button.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}