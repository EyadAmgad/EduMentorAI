// Minimalist Chat JavaScript with Enhanced Text Rendering

document.addEventListener('DOMContentLoaded', function() {
    // Configure marked for optimal rendering
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            sanitize: false,
            silent: false,
            headerIds: false,
            mangle: false,
            // Better text rendering options
            smartypants: false,
            xhtml: false
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
    let autoResizeDebounce = null;
    
    // Enhanced auto-resize with better performance
    chatInput.addEventListener('input', function() {
        clearTimeout(autoResizeDebounce);
        autoResizeDebounce = setTimeout(() => {
            const currentHeight = this.scrollHeight;
            const minHeight = 50;
            const maxHeight = 150;
            
            // Only update if height actually changed
            const newHeight = Math.min(Math.max(currentHeight, minHeight), maxHeight);
            if (this.style.height !== newHeight + 'px') {
                this.style.height = 'auto';
                this.style.height = newHeight + 'px';
            }
        }, 5);
    });

    // Refined keyboard shortcuts
    chatInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            if (event.shiftKey || event.ctrlKey || event.metaKey) {
                // Allow new line with modifiers
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

    // Simplified mobile sidebar
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

    // Enhanced form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (!message || isStreaming) return;

        // Set loading state
        setLoadingState(true);
        
        // Add user message
        addMessage('user', message, true);
        
        // Clear and reset input
        chatInput.value = '';
        chatInput.style.height = 'auto';
        chatInput.focus();

        // Send message
        sendStreamingMessage(message);
    });

    // Optimized streaming with better text rendering
    function sendStreamingMessage(message) {
        isStreaming = true;
        const thinkingIndicator = showThinkingIndicator();
        
        let aiMessageDiv = null;
        let messageContent = null;
        let accumulatedContent = '';
        let renderTimeout = null;
        
        // Prepare streaming URL
        let streamUrl = config.streamUrl || '/chat/stream/';
        if (currentSessionId) {
            streamUrl = `/chat/${currentSessionId}/stream/`;
        }
        
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
                    // Final render and cleanup
                    if (renderTimeout) {
                        clearTimeout(renderTimeout);
                        if (messageContent && accumulatedContent) {
                            updateMessageContent(messageContent, accumulatedContent, true);
                        }
                    }
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
                    
                    // Debounced rendering for better performance
                    clearTimeout(renderTimeout);
                    renderTimeout = setTimeout(() => {
                        updateMessageContent(messageContent, accumulatedContent, false);
                        scrollToBottomSmooth();
                    }, 50); // Render every 50ms for smooth updates
                    break;
                    
                case 'complete':
                    if (data.session_id) {
                        currentSessionId = data.session_id;
                        updateURL(`/chat/${data.session_id}/`);
                    }
                    
                    if (messageContent) {
                        // Final render
                        clearTimeout(renderTimeout);
                        updateMessageContent(messageContent, accumulatedContent, true);
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

    // Enhanced message content updating with better text rendering
    function updateMessageContent(messageElement, content, isFinal = false) {
        if (!messageElement || !content) return;
        
        try {
            let renderedContent;
            
            if (typeof marked !== 'undefined') {
                renderedContent = marked.parse(content);
            } else {
                renderedContent = escapeHtml(content).replace(/\n/g, '<br>');
            }
            
            // Use DocumentFragment for better performance during streaming
            if (!isFinal) {
                const fragment = document.createDocumentFragment();
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = renderedContent;
                
                while (tempDiv.firstChild) {
                    fragment.appendChild(tempDiv.firstChild);
                }
                
                // Clear and append in one operation
                messageElement.innerHTML = '';
                messageElement.appendChild(fragment);
            } else {
                // Final render - can use innerHTML safely
                messageElement.innerHTML = renderedContent;
            }
            
        } catch (error) {
            console.warn('Content rendering failed:', error);
            messageElement.textContent = content;
        }
    }

    // Refined thinking indicator
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
            // Gentle fade out
            thinkingIndicator.style.transition = 'opacity 0.2s ease';
            thinkingIndicator.style.opacity = '0';
            setTimeout(() => {
                if (thinkingIndicator.parentNode) {
                    thinkingIndicator.remove();
                }
            }, 200);
        }
    }

    // Simplified message creation
    function addMessage(role, content, animate = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        if (animate) {
            messageDiv.style.opacity = '0';
            messageDiv.style.transform = 'translateY(12px)';
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
            updateMessageContent(messageContent, content, true);
        }

        if (role === 'user') {
            addMessageTimestamp(messageContent);
            addMessageActions(messageDiv, content);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        
        if (animate) {
            // Simple fade in
            requestAnimationFrame(() => {
                messageDiv.style.transition = 'all 0.3s ease';
                messageDiv.style.opacity = '1';
                messageDiv.style.transform = 'translateY(0)';
            });
        }
        
        scrollToBottomSmooth();
        return messageDiv;
    }

    function addMessageTimestamp(messageContent) {
        const existingTime = messageContent.querySelector('.message-time');
        if (existingTime) return;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = formatTimestamp(new Date());
        messageContent.appendChild(timeDiv);
    }

    // Simplified message actions
    function addMessageActions(messageDiv, content) {
        const existingActions = messageDiv.querySelector('.message-actions');
        if (existingActions) return;
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        const copyBtn = document.createElement('button');
        copyBtn.className = 'message-action-btn';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy message';
        copyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            copyMessage(content);
        });
        
        actionsDiv.appendChild(copyBtn);
        messageDiv.appendChild(actionsDiv);
    }

    // Enhanced copy functionality
    function copyMessage(text) {
        const cleanText = text
            .replace(/<[^>]*>/g, '') // Remove HTML tags
            .replace(/&nbsp;/g, ' ') // Replace &nbsp; with spaces
            .replace(/&lt;/g, '<') // Replace &lt; with <
            .replace(/&gt;/g, '>') // Replace &gt; with >
            .replace(/&amp;/g, '&') // Replace &amp; with &
            .trim();
        
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(cleanText)
                .then(() => showCopyFeedback('Copied!'))
                .catch(() => fallbackCopyText(cleanText));
        } else {
            fallbackCopyText(cleanText);
        }
    }

    function fallbackCopyText(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-9999px';
        textArea.style.top = '-9999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            const successful = document.execCommand('copy');
            showCopyFeedback(successful ? 'Copied!' : 'Copy failed');
        } catch (err) {
            showCopyFeedback('Copy failed');
        }
        
        document.body.removeChild(textArea);
    }

    function showCopyFeedback(message) {
        const feedback = document.createElement('div');
        feedback.className = 'copy-feedback';
        feedback.textContent = message;
        
        document.body.appendChild(feedback);
        
        setTimeout(() => {
            feedback.style.transition = 'all 0.2s ease';
            feedback.style.opacity = '0';
            feedback.style.transform = 'translateX(100%)';
            setTimeout(() => feedback.remove(), 200);
        }, 2000);
    }

    // Optimized smooth scrolling
    function scrollToBottomSmooth() {
        if (chatMessages.dataset.userScrolled !== 'true') {
            requestAnimationFrame(() => {
                chatMessages.scrollTo({
                    top: chatMessages.scrollHeight,
                    behavior: 'smooth'
                });
            });
        }
    }

    // Track user scrolling to prevent auto-scroll interference
    let scrollTimeout;
    chatMessages.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        
        const isAtBottom = chatMessages.scrollTop + chatMessages.clientHeight >= chatMessages.scrollHeight - 100;
        
        if (isAtBottom) {
            chatMessages.dataset.userScrolled = 'false';
        } else {
            chatMessages.dataset.userScrolled = 'true';
        }
        
        scrollTimeout = setTimeout(() => {
            chatMessages.dataset.userScrolled = 'false';
        }, 3000);
    });

    // Simplified loading state
    function setLoadingState(loading) {
        sendBtn.disabled = loading;
        chatInput.disabled = loading;
        
        if (loading) {
            sendBtn.classList.add('loading');
            sendBtn.innerHTML = '';
        } else {
            sendBtn.classList.remove('loading');
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            setTimeout(() => chatInput.focus(), 100);
        }
    }

    // Simplified error handling
    function handleStreamingError(error, thinkingIndicator = null) {
        console.error('Streaming error:', error);
        
        if (thinkingIndicator) {
            hideThinkingIndicator();
        }
        
        const errorMessage = error.message || 'Sorry, I encountered an error. Please try again.';
        addMessage('ai', `⚠️ ${errorMessage}`, true);
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

    // Initialize
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
        if (chatInput && !window.matchMedia('(max-width: 768px)').matches) {
            chatInput.focus();
        }
    }, 300);

    // Optimized resize handling
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.innerWidth > 768) {
                closeSidebar();
            }
        }, 100);
    });
});

// Global functions for template compatibility
window.setSuggestedPrompt = function(prompt) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = prompt;
        chatInput.focus();
        chatInput.dispatchEvent(new Event('input'));
    }
};

window.loadChatSession = function(sessionId) {
    // Simple loading transition
    document.body.style.transition = 'opacity 0.2s ease';
    document.body.style.opacity = '0.8';
    
    setTimeout(() => {
        window.location.href = `/chat/${sessionId}/`;
    }, 200);
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

window.startNewChat = function() {
    const chatUrl = window.chatConfig?.chatUrl || '/chat/';
    document.body.style.opacity = '0.9';
    setTimeout(() => window.location.href = chatUrl, 150);
};

// Enhanced new chat button handling
document.addEventListener('DOMContentLoaded', function() {
    const newChatBtn = document.querySelector('.new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.startNewChat();
        });
    }
});