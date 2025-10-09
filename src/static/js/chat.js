// Enhanced Chat JavaScript with Modern Features and Improved UX

document.addEventListener('DOMContentLoaded', function() {
    // Configure marked for safe rendering with enhanced options
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            sanitize: false,
            silent: false,
            headerIds: false,
            mangle: false
        });
    }
    
    // DOM Elements
    const chatInput = document.getElementById('chatInput');
    const chatForm = document.getElementById('chatForm');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
    const chatSidebar = document.getElementById('chatSidebar');
    const chatOverlay = document.getElementById('chatOverlay');
    
    // Configuration
    const config = window.chatConfig || {};
    let currentSessionId = config.sessionId;
    let isStreaming = false;
    
    // Enhanced auto-resize textarea with better performance
    let resizeTimeout;
    chatInput.addEventListener('input', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            this.style.height = 'auto';
            const newHeight = Math.min(Math.max(this.scrollHeight, 56), 180);
            this.style.height = newHeight + 'px';
        }, 10);
    });

    // Enhanced keyboard shortcuts
    chatInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            if (event.shiftKey || event.ctrlKey) {
                // Allow new line with Shift+Enter or Ctrl+Enter
                return;
            } else {
                // Send message with Enter
                event.preventDefault();
                if (!isStreaming && this.value.trim()) {
                    chatForm.dispatchEvent(new Event('submit', { bubbles: true }));
                }
            }
        } else if (event.key === 'Escape') {
            // Clear input with Escape
            if (this.value) {
                this.value = '';
                this.style.height = 'auto';
                event.preventDefault();
            }
        }
    });

    // Enhanced mobile sidebar with better animations
    if (mobileSidebarToggle) {
        mobileSidebarToggle.addEventListener('click', function() {
            const isOpen = chatSidebar.classList.contains('show');
            
            if (isOpen) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    if (chatOverlay) {
        chatOverlay.addEventListener('click', closeSidebar);
    }

    // Sidebar functions
    function openSidebar() {
        chatSidebar.classList.add('show');
        chatOverlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        chatSidebar.classList.remove('show');
        chatOverlay.classList.remove('show');
        document.body.style.overflow = '';
    }

    // Enhanced form submission with better UX
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (!message || isStreaming) return;

        // Set loading state
        setLoadingState(true);
        
        // Add user message with animation
        addMessage('user', message, true);
        
        // Clear and reset input
        chatInput.value = '';
        chatInput.style.height = 'auto';
        chatInput.focus();

        // Send message with streaming
        sendStreamingMessage(message);
    });

    // Enhanced streaming message function
    function sendStreamingMessage(message) {
        isStreaming = true;
        const thinkingIndicator = showThinkingIndicator();
        
        let aiMessageDiv = null;
        let messageContent = null;
        let accumulatedContent = '';
        
        // Prepare streaming URL
        let streamUrl = config.streamUrl || '/chat/stream/';
        if (currentSessionId) {
            streamUrl = `/chat/${currentSessionId}/stream/`;
        }
        
        // Enhanced fetch with better error handling
        fetch(streamUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            return readStreamRecursive(reader, decoder);
        })
        .catch(error => {
            console.error('Streaming error:', error);
            handleStreamingError(error, thinkingIndicator);
        })
        .finally(() => {
            isStreaming = false;
            setLoadingState(false);
        });
        
        function readStreamRecursive(reader, decoder) {
            return reader.read().then(({ done, value }) => {
                if (done) {
                    return;
                }
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                lines.forEach(line => {
                    if (line.startsWith('data: ') && line.length > 6) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            handleStreamData(data);
                        } catch (e) {
                            console.warn('Failed to parse streaming data:', line);
                        }
                    }
                });
                
                return readStreamRecursive(reader, decoder);
            });
        }
        
        function handleStreamData(data) {
            switch (data.type) {
                case 'start':
                    // Keep thinking indicator
                    break;
                    
                case 'chunk':
                    if (!aiMessageDiv) {
                        hideThinkingIndicator();
                        aiMessageDiv = addMessage('ai', '', false);
                        messageContent = aiMessageDiv.querySelector('.message-content');
                    }
                    
                    accumulatedContent += data.content;
                    updateMessageContent(messageContent, accumulatedContent);
                    scrollToBottomSmooth();
                    break;
                    
                case 'complete':
                    if (data.session_id) {
                        currentSessionId = data.session_id;
                        updateURL(`/chat/${data.session_id}/`);
                    }
                    
                    if (messageContent) {
                        addMessageTimestamp(messageContent);
                        addMessageActions(aiMessageDiv, accumulatedContent);
                    }
                    break;
                    
                case 'error':
                    handleStreamingError(new Error(data.error || 'Unknown error'), thinkingIndicator);
                    break;
            }
        }
    }

    // Enhanced message content updating
    function updateMessageContent(messageElement, content) {
        try {
            if (typeof marked !== 'undefined') {
                messageElement.innerHTML = marked.parse(content);
            } else {
                messageElement.innerHTML = content.replace(/\n/g, '<br>');
            }
        } catch (error) {
            console.warn('Markdown parsing failed:', error);
            messageElement.innerHTML = escapeHtml(content).replace(/\n/g, '<br>');
        }
    }

    // Enhanced thinking indicator with better animations
    function showThinkingIndicator() {
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'thinking-indicator';
        thinkingDiv.id = 'thinking-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
        
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
        scrollToBottomSmooth();
        
        return thinkingDiv;
    }

    function hideThinkingIndicator() {
        const thinkingIndicator = document.getElementById('thinking-indicator');
        if (thinkingIndicator) {
            thinkingIndicator.style.opacity = '0';
            thinkingIndicator.style.transform = 'translateY(-10px)';
            setTimeout(() => thinkingIndicator.remove(), 200);
        }
    }

    // Enhanced message creation with better animations
    function addMessage(role, content, animate = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        if (animate) {
            messageDiv.style.opacity = '0';
            messageDiv.style.transform = 'translateY(20px) scale(0.95)';
        }
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (role === 'user') {
            avatar.textContent = config.userInitial || 'U';
        } else {
            avatar.innerHTML = '<i class="fas fa-robot"></i>';
        }

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (content) {
            updateMessageContent(messageContent, content);
        }

        if (role === 'user') {
            addMessageTimestamp(messageContent);
            addMessageActions(messageDiv, content);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        
        if (animate) {
            // Trigger animation
            setTimeout(() => {
                messageDiv.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
                messageDiv.style.opacity = '1';
                messageDiv.style.transform = 'translateY(0) scale(1)';
            }, 10);
        }
        
        scrollToBottomSmooth();
        return messageDiv;
    }

    // Add message timestamp
    function addMessageTimestamp(messageContent) {
        const existingTime = messageContent.querySelector('.message-time');
        if (existingTime) return;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = formatTimestamp(new Date());
        messageContent.appendChild(timeDiv);
    }

    // Enhanced message actions
    function addMessageActions(messageDiv, content) {
        const existingActions = messageDiv.querySelector('.message-actions');
        if (existingActions) return;
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'message-action-btn';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy message';
        copyBtn.addEventListener('click', () => copyMessage(content));
        
        actionsDiv.appendChild(copyBtn);
        messageDiv.appendChild(actionsDiv);
    }

    // Copy message functionality with toast feedback
    function copyMessage(text) {
        // Clean text for copying
        const cleanText = text.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(cleanText)
                .then(() => showCopyFeedback('Message copied!'))
                .catch(() => fallbackCopyText(cleanText));
        } else {
            fallbackCopyText(cleanText);
        }
    }

    function fallbackCopyText(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            showCopyFeedback('Message copied!');
        } catch (err) {
            showCopyFeedback('Copy failed', 'error');
        }
        
        document.body.removeChild(textArea);
    }

    function showCopyFeedback(message, type = 'success') {
        const feedback = document.createElement('div');
        feedback.className = 'copy-feedback';
        feedback.textContent = message;
        
        if (type === 'error') {
            feedback.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
        }
        
        document.body.appendChild(feedback);
        
        setTimeout(() => {
            feedback.style.opacity = '0';
            feedback.style.transform = 'translateX(100%)';
            setTimeout(() => feedback.remove(), 300);
        }, 2000);
    }

    // Enhanced smooth scrolling
    function scrollToBottomSmooth() {
        requestAnimationFrame(() => {
            chatMessages.scrollTo({
                top: chatMessages.scrollHeight,
                behavior: 'smooth'
            });
        });
    }

    // Loading state management
    function setLoadingState(loading) {
        sendBtn.disabled = loading;
        chatInput.disabled = loading;
        
        if (loading) {
            sendBtn.classList.add('loading');
            sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        } else {
            sendBtn.classList.remove('loading');
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            setTimeout(() => chatInput.focus(), 100);
        }
    }

    // Enhanced error handling
    function handleStreamingError(error, thinkingIndicator = null) {
        console.error('Streaming error:', error);
        
        if (thinkingIndicator) {
            hideThinkingIndicator();
        }
        
        const errorMessage = error.message || 'Sorry, I encountered an error. Please try again.';
        const aiMessageDiv = addMessage('ai', `⚠️ ${errorMessage}`, true);
        
        // Add retry button for network errors
        if (error.message.includes('HTTP') || error.message.includes('Network')) {
            setTimeout(() => {
                const messageContent = aiMessageDiv.querySelector('.message-content');
                const retryBtn = document.createElement('button');
                retryBtn.className = 'btn btn-sm btn-outline-primary mt-2';
                retryBtn.innerHTML = '<i class="fas fa-redo me-1"></i>Retry';
                retryBtn.addEventListener('click', () => {
                    // Get the last user message to retry
                    const messages = chatMessages.querySelectorAll('.message.user');
                    if (messages.length > 0) {
                        const lastMessage = messages[messages.length - 1];
                        const lastText = lastMessage.querySelector('.message-content').textContent;
                        aiMessageDiv.remove();
                        sendStreamingMessage(lastText.replace(/\d{1,2}[/:.]\d{1,2}[/:.]\d{2,4}[, ]+\d{1,2}[:.:]\d{2}.*$/, '').trim());
                    }
                });
                messageContent.appendChild(retryBtn);
            }, 500);
        }
    }

    // Utility functions
    function getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }

    function updateURL(url) {
        try {
            window.history.replaceState({}, '', url);
        } catch (e) {
            console.warn('Could not update URL:', e);
        }
    }

    function formatTimestamp(date) {
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
        
        return date.toLocaleDateString(undefined, { 
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Enhanced scroll to bottom on page load
    function initialScroll() {
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);
    }

    // Intersection Observer for auto-scroll behavior
    const observeLastMessage = () => {
        const messages = chatMessages.querySelectorAll('.message');
        if (messages.length === 0) return;
        
        const lastMessage = messages[messages.length - 1];
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // User is at bottom, continue auto-scrolling
                    chatMessages.dataset.autoScroll = 'true';
                } else {
                    // User scrolled up, pause auto-scrolling
                    chatMessages.dataset.autoScroll = 'false';
                }
            });
        }, { threshold: 0.1 });
        
        observer.observe(lastMessage);
    };

    // Enhanced resize handling
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.innerWidth > 768) {
                closeSidebar();
            }
            scrollToBottomSmooth();
        }, 100);
    });

    // Initialize
    initialScroll();
    observeLastMessage();
    
    // Focus input on load
    setTimeout(() => {
        if (chatInput && !window.matchMedia('(max-width: 768px)').matches) {
            chatInput.focus();
        }
    }, 500);
});

// Global functions for template compatibility
window.setSuggestedPrompt = function(prompt) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = prompt;
        chatInput.focus();
        
        // Trigger input event for auto-resize
        chatInput.dispatchEvent(new Event('input'));
    }
};

window.loadChatSession = function(sessionId) {
    // Add loading state
    const loader = document.createElement('div');
    loader.className = 'position-fixed top-50 start-50 translate-middle text-center';
    loader.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
    document.body.appendChild(loader);
    
    setTimeout(() => {
        window.location.href = `/chat/${sessionId}/`;
    }, 300);
};

window.showChatModeModal = function() {
    const modal = document.getElementById('chatModeModal');
    if (modal && typeof bootstrap !== 'undefined') {
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
    }
};

window.setChatMode = function(mode) {
    const documentSection = document.getElementById('documentSection');
    const subjectSection = document.getElementById('subjectSection');
    
    if (documentSection && subjectSection) {
        if (mode === 'document') {
            documentSection.style.display = 'block';
            subjectSection.style.display = 'none';
        } else if (mode === 'subject') {
            documentSection.style.display = 'none';
            subjectSection.style.display = 'block';
        }
    }
};

// Enhanced new chat function
window.startNewChat = function() {
    const chatUrl = window.chatConfig?.chatUrl || '/chat/';
    
    // Add smooth transition effect
    document.body.style.opacity = '0.8';
    setTimeout(() => {
        window.location.href = chatUrl;
    }, 200);
};

// Add click handler for new chat button if it exists
document.addEventListener('DOMContentLoaded', function() {
    const newChatBtn = document.querySelector('[href*="chat"][class*="new-chat"], .new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.startNewChat();
        });
    }
});