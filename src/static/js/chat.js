document.addEventListener('DOMContentLoaded', function() {
    // Configure marked for safe rendering
    marked.setOptions({
        breaks: true,
        gfm: true,
        sanitize: false,
        silent: false
    });
    
    const chatInput = document.getElementById('chatInput');
    const chatForm = document.getElementById('chatForm');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
    const chatSidebar = document.getElementById('chatSidebar');
    const chatOverlay = document.getElementById('chatOverlay');
    
    // Track current session ID
    let currentSessionId = {% if session %}'{{ session.id }}'{% else %}null{% endif %};

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });

    // Mobile sidebar toggle
    if (mobileSidebarToggle) {
        mobileSidebarToggle.addEventListener('click', function() {
            chatSidebar.classList.toggle('show');
            chatOverlay.classList.toggle('show');
        });
    }

    if (chatOverlay) {
        chatOverlay.addEventListener('click', function() {
            chatSidebar.classList.remove('show');
            chatOverlay.classList.remove('show');
        });
    }

    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (!message) return;

        // Disable form
        sendBtn.disabled = true;
        chatInput.disabled = true;

        // Add user message to chat
        addMessage('user', message);
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Prepare URL based on session
        let url = '{% url "rag_app:chat" %}';
        if (currentSessionId) {
            url = '/chat/' + currentSessionId + '/';
        }

        // Send message with real streaming
        sendStreamingMessage(message);
    });



    // Send streaming message with real-time display
    function sendStreamingMessage(message) {
        // Show thinking indicator while waiting
        const thinkingIndicator = showThinkingIndicator();
        
        let aiMessageDiv = null;
        let messageContent = null;
        let accumulatedContent = '';
        
        // Prepare streaming URL
        let streamUrl = '{% url "rag_app:chat_stream" %}';
        if (currentSessionId) {
            streamUrl = '/chat/' + currentSessionId + '/stream/';
        }
        
        // Send POST request and read streaming response
        fetch(streamUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
            body: JSON.stringify({
                'message': message
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            function readStream() {
                return reader.read().then(({ done, value }) => {
                    if (done) {
                        // Re-enable form when streaming is complete
                        sendBtn.disabled = false;
                        chatInput.disabled = false;
                        chatInput.focus();
                        return;
                    }
                    
                    // Decode chunk and process lines
                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');
                    
                    lines.forEach(line => {
                        if (line.startsWith('data: ') && line.length > 6) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                
                                if (data.type === 'start') {
                                    // Keep thinking indicator for now
                                    
                                } else if (data.type === 'chunk') {
                                    // Replace thinking indicator with actual message on first chunk
                                    if (!aiMessageDiv) {
                                        hideThinkingIndicator();
                                        aiMessageDiv = addMessage('ai', '');
                                        messageContent = aiMessageDiv.querySelector('.message-content');
                                    }
                                    
                                    accumulatedContent += data.content;
                                    // Update message content with markdown parsing
                                    try {
                                        messageContent.innerHTML = marked.parse(accumulatedContent);
                                    } catch (e) {
                                        messageContent.innerHTML = accumulatedContent.replace(/\n/g, '<br>');
                                    }
                                    scrollToBottom();
                                    
                                } else if (data.type === 'complete') {
                                    if (data.session_id) {
                                        currentSessionId = data.session_id;
                                        const newUrl = '/chat/' + data.session_id + '/';
                                        window.history.replaceState({}, '', newUrl);
                                    }
                                    // Add timestamp
                                    const timeDiv = document.createElement('div');
                                    timeDiv.className = 'message-time';
                                    timeDiv.textContent = new Date().toLocaleString();
                                    messageContent.appendChild(timeDiv);
                                    
                                } else if (data.type === 'error') {
                                    // Replace thinking indicator with error message
                                    if (!aiMessageDiv) {
                                        hideThinkingIndicator();
                                        aiMessageDiv = addMessage('ai', '');
                                        messageContent = aiMessageDiv.querySelector('.message-content');
                                    }
                                    messageContent.textContent = data.error || 'Sorry, I encountered an error.';
                                }
                            } catch (e) {
                                console.warn('Failed to parse streaming data:', line);
                            }
                        }
                    });
                    
                    return readStream();
                });
            }
            
            return readStream();
        })
        .catch(error => {
            console.error('Streaming error:', error);
            hideThinkingIndicator();
            
            // Create error message if no AI message exists yet
            if (!aiMessageDiv) {
                aiMessageDiv = addMessage('ai', '');
                messageContent = aiMessageDiv.querySelector('.message-content');
            }
            messageContent.textContent = 'Sorry, I encountered an error. Please try again.';
            sendBtn.disabled = false;
            chatInput.disabled = false;
            chatInput.focus();
        });
    }

    // Show thinking indicator
    function showThinkingIndicator() {
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'thinking-indicator';
        thinkingDiv.id = 'thinking-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
        avatar.style.background = 'var(--secondary-color)';
        avatar.style.color = 'white';
        
        const thinkingContent = document.createElement('div');
        thinkingContent.className = 'thinking-content';
        
        const thinkingText = document.createElement('span');
        thinkingText.textContent = 'Thinking';
        
        const thinkingDots = document.createElement('div');
        thinkingDots.className = 'thinking-dots';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'thinking-dot';
            thinkingDots.appendChild(dot);
        }
        
        thinkingContent.appendChild(thinkingText);
        thinkingContent.appendChild(thinkingDots);
        
        thinkingDiv.appendChild(avatar);
        thinkingDiv.appendChild(thinkingContent);
        
        chatMessages.appendChild(thinkingDiv);
        scrollToBottom();
        
        return thinkingDiv;
    }

    // Hide thinking indicator
    function hideThinkingIndicator() {
        const thinkingIndicator = document.getElementById('thinking-indicator');
        if (thinkingIndicator) {
            thinkingIndicator.remove();
        }
    }

    // Scroll to bottom of messages
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Add message to chat
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
            // For user messages, just convert newlines to <br>
            messageContent.innerHTML = content.replace(/\n/g, '<br>');
        } else if (content) {
            // For AI messages, render markdown
            try {
                messageContent.innerHTML = marked.parse(content);
            } catch (error) {
                console.warn('Markdown parsing failed, using plain text:', error);
                messageContent.innerHTML = content.replace(/\n/g, '<br>');
            }
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleString();
        messageContent.appendChild(timeDiv);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        chatMessages.appendChild(messageDiv);
        scrollToBottom();
        
        return messageDiv; // Return the message element for streaming updates
    }

    // Initial scroll to bottom
    scrollToBottom();
});

// Set suggested prompt
function setSuggestedPrompt(prompt) {
    document.getElementById('chatInput').value = prompt;
    document.getElementById('chatInput').focus();
}

// Load chat session
function loadChatSession(sessionId) {
    window.location.href = '/chat/' + sessionId + '/';
}

// Start new chat
document.getElementById('newChatBtn').addEventListener('click', function(e) {
    e.preventDefault();
    window.location.href = '{% url "rag_app:chat" %}';
});

// Chat mode selection
function showChatModeModal() {
    const modal = new bootstrap.Modal(document.getElementById('chatModeModal'));
    modal.show();
}

function setChatMode(mode) {
    const documentSection = document.getElementById('documentSection');
    const subjectSection = document.getElementById('subjectSection');
    
    if (mode === 'document') {
        documentSection.style.display = 'block';
        subjectSection.style.display = 'none';
    } else if (mode === 'subject') {
        documentSection.style.display = 'none';
        subjectSection.style.display = 'block';
    }
}