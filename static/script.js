
class HealthcareChatbot {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.themeToggle = document.getElementById('themeToggle');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        this.messageCount = 0;
        this.isProcessing = false;
        this.chatbotName = 'Dr. Alex';
        this.currentLanguage = 'en';
        
        this.initializeEventListeners();
        this.initializeTheme();
        this.addStatusIndicator();
        this.addControlButtons();
        this.loadChatHistory();
        this.addInitialWelcomeMessage();
    }
    
    initializeEventListeners() {
        // Send message on button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter key press
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        this.userInput.addEventListener('input', () => {
            this.autoResizeInput();
        });
        
        // Theme toggle
        this.themeToggle.addEventListener('click', () => this.toggleTheme());
        
        // Copy message on click
        this.chatMessages.addEventListener('click', (e) => {
            if (e.target.closest('.bot-message .message-bubble')) {
                this.copyToClipboard(e.target.closest('.message-bubble'));
            }
        });
        
        // Auto-focus input
        this.userInput.focus();
        
        // Prevent form submission
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target === this.userInput && !e.shiftKey) {
                e.preventDefault();
            }
        });
    }
    
    addControlButtons() {
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'chat-controls';
        controlsDiv.innerHTML = `
            <button id="clearHistoryBtn" class="control-btn" title="Clear chat history">
                🗑️ Clear History
            </button>
            <button id="historyBtn" class="control-btn" title="View chat history">
                📋 History
            </button>
            <select id="languageSelect" class="control-select" title="Select language">
                <option value="en">🇺🇸 English</option>
                <option value="es">🇪🇸 Español</option>
                <option value="hi">🇮🇳 हिंदी</option>
            </select>
        `;
        
        // Insert before chat container
        const container = document.querySelector('.container');
        const chatContainer = document.querySelector('.chat-container');
        container.insertBefore(controlsDiv, chatContainer);
        
        // Add event listeners
        document.getElementById('clearHistoryBtn').addEventListener('click', () => this.clearHistory());
        document.getElementById('historyBtn').addEventListener('click', () => this.showHistory());
        document.getElementById('languageSelect').addEventListener('change', (e) => this.changeLanguage(e.target.value));
    }
    
    autoResizeInput() {
        this.userInput.style.height = 'auto';
        this.userInput.style.height = Math.min(this.userInput.scrollHeight, 120) + 'px';
    }
    
    initializeTheme() {
        const savedTheme = localStorage.getItem('healthcare-chatbot-theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateThemeIcon(savedTheme);
    }
    
    updateThemeIcon(theme) {
        const sunIcon = this.themeToggle.querySelector('.sun-icon');
        const moonIcon = this.themeToggle.querySelector('.moon-icon');
        
        if (theme === 'dark') {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
        } else {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
        }
    }
    
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('healthcare-chatbot-theme', newTheme);
        this.updateThemeIcon(newTheme);
        
        // Show brief notification
        this.showStatusMessage(`Switched to ${newTheme} mode`, 'theme-change');
    }
    
    addStatusIndicator() {
        const statusIndicator = document.createElement('div');
        statusIndicator.className = 'status-indicator offline';
        statusIndicator.textContent = '🔒 Offline Mode';
        statusIndicator.id = 'statusIndicator';
        document.body.appendChild(statusIndicator);
        
        // Show status briefly on load
        setTimeout(() => {
            statusIndicator.classList.add('show');
            setTimeout(() => {
                statusIndicator.classList.remove('show');
            }, 3000);
        }, 1000);
    }
    
    addInitialWelcomeMessage() {
        // Remove the static welcome message since we'll add it dynamically
        const staticMessage = this.chatMessages.querySelector('.message');
        if (staticMessage) {
            staticMessage.remove();
        }
        
        // Add enhanced welcome message
        setTimeout(() => {
            const welcomeText = `👋 Hello! I'm ${this.chatbotName}, your AI-powered healthcare assistant running completely offline for your privacy and security.

I can help you with:
🩺 Symptoms and health conditions
💊 General medical information  
📅 Doctor appointments and procedures
🏥 Health insurance guidance
🚨 Emergency first aid procedures
🧠 Mental health support tips
🌍 Available in English and Spanish

Ask me anything about healthcare! I use advanced natural language processing to understand your questions and provide helpful responses.

✨ *Try asking: "What are the symptoms of diabetes?" or "¿Cuáles son los síntomas de diabetes?"*

💡 You can also ask me "What can I call you?" to learn more about me!`;
            
            this.addMessage(welcomeText, 'bot', 100);
        }, 500);
    }
    
    async loadChatHistory() {
        try {
            const response = await fetch('/chat/history');
            if (response.ok) {
                const data = await response.json();
                if (data.history.length > 0) {
                    this.showStatusMessage(`📚 Loaded ${data.history.length} previous messages`, 'info');
                }
            }
        } catch (error) {
            console.error('Failed to load chat history:', error);
        }
    }
    
    async clearHistory() {
        try {
            const response = await fetch('/chat/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Clear visual chat
                const messages = this.chatMessages.querySelectorAll('.message');
                messages.forEach((msg, index) => {
                    setTimeout(() => {
                        msg.style.opacity = '0';
                        msg.style.transform = 'translateY(-20px)';
                        setTimeout(() => msg.remove(), 300);
                    }, index * 50);
                });
                
                // Add clear confirmation message
                setTimeout(() => {
                    this.addMessage(data.message, 'bot', 100);
                    this.showStatusMessage('🧹 Chat history cleared', 'success');
                }, 1000);
            }
        } catch (error) {
            console.error('Failed to clear history:', error);
            this.showStatusMessage('❌ Failed to clear history', 'error');
        }
    }
    
    async showHistory() {
        try {
            const response = await fetch('/chat/history');
            if (response.ok) {
                const data = await response.json();
                
                if (data.history.length === 0) {
                    this.showStatusMessage('📭 No chat history found', 'info');
                    return;
                }
                
                let historyText = `📋 **Chat History Summary** (${data.history.length} messages):\n\n`;
                data.history.slice(-5).forEach((entry, index) => {
                    const time = entry.ist_display || new Date(entry.timestamp).toLocaleTimeString();
                    const lang = entry.language === 'es' ? '🇪🇸' : entry.language === 'hi' ? '🇮🇳' : '🇺🇸';
                    historyText += `${lang} **${time}**\n`;
                    historyText += `❓ ${entry.user_message.substring(0, 50)}${entry.user_message.length > 50 ? '...' : ''}\n`;
                    historyText += `💬 ${entry.bot_response.substring(0, 100)}${entry.bot_response.length > 100 ? '...' : ''}\n\n`;
                });
                
                historyText += `*Showing last 5 conversations. Total: ${data.history.length} messages.*`;
                this.addMessage(historyText, 'bot', 100);
            }
        } catch (error) {
            console.error('Failed to load history:', error);
            this.showStatusMessage('❌ Failed to load history', 'error');
        }
    }
    
    async changeLanguage(language) {
        try {
            const response = await fetch('/language', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ language: language })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.currentLanguage = language;
                this.addMessage(data.message, 'bot', 100);
                this.showStatusMessage(`🌍 Language changed to ${language === 'es' ? 'Español' : language === 'hi' ? 'हिंदी' : 'English'}`, 'success');
                
                // Update placeholder text
                const placeholder = language === 'es' ? 'Pregúntame sobre salud...' : 
                                   language === 'hi' ? 'स्वास्थ्य के बारे में पूछें...' : 
                                   'Ask me about healthcare...';
                this.userInput.placeholder = placeholder;
            }
        } catch (error) {
            console.error('Failed to change language:', error);
            this.showStatusMessage('❌ Failed to change language', 'error');
        }
    }
    
    showStatusMessage(message, type = 'info') {
        const statusIndicator = document.getElementById('statusIndicator');
        const originalText = statusIndicator.textContent;
        const originalClass = statusIndicator.className;
        
        statusIndicator.textContent = message;
        statusIndicator.className = `status-indicator ${type} show`;
        
        setTimeout(() => {
            statusIndicator.textContent = originalText;
            statusIndicator.className = originalClass;
        }, 2000);
    }
    
    async sendMessage() {
        const message = this.userInput.value.trim();
        
        if (!message || this.isProcessing) return;
        
        // Set processing state
        this.isProcessing = true;
        this.setInputState(false);
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear and reset input
        this.userInput.value = '';
        this.autoResizeInput();
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Show processing status
        this.showStatusMessage('🤖 Processing...', 'processing');
        
        try {
            // Send request to backend
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Update chatbot name if received
            if (data.chatbot_name) {
                this.chatbotName = data.chatbot_name;
            }
            
            // Update current language
            if (data.language) {
                this.currentLanguage = data.language;
                document.getElementById('languageSelect').value = data.language;
            }
            
            // Simulate realistic processing time
            const processingTime = Math.max(800, Math.min(2000, message.length * 50));
            await this.delay(processingTime);
            
            // Hide typing indicator and add bot response
            this.hideTypingIndicator();
            this.addMessage(data.response, 'bot', data.confidence, data.status);
            
        } catch (error) {
            console.error('Error:', error);
            this.hideTypingIndicator();
            this.addMessage(
                '⚠️ I encountered a technical issue. Please try again in a moment. If the problem persists, please refresh the page.',
                'bot',
                0,
                'error'
            );
            this.showStatusMessage('❌ Error occurred', 'error');
        } finally {
            // Reset processing state
            this.isProcessing = false;
            this.setInputState(true);
            this.userInput.focus();
        }
    }
    
    addMessage(content, type, confidence = null, status = null) {
        this.messageCount++;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        messageDiv.style.animationDelay = '0.1s';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        
        // Format message content with proper line breaks
        const formattedContent = this.formatMessageContent(content);
        messageBubble.innerHTML = formattedContent;
        
        messageContent.appendChild(messageBubble);
        
        // Add confidence indicator for bot messages
        if (type === 'bot' && confidence !== null) {
            const confidenceDiv = this.createConfidenceIndicator(confidence, status);
            messageContent.appendChild(confidenceDiv);
        }
        
        // Add copy notification element for bot messages
        if (type === 'bot') {
            const copyNotification = document.createElement('div');
            copyNotification.className = 'copy-notification';
            copyNotification.textContent = '📋 Copied!';
            messageBubble.appendChild(copyNotification);
        }
        
        messageDiv.appendChild(messageContent);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Trigger animation
        setTimeout(() => {
            messageDiv.style.opacity = '1';
        }, 50);
    }
    
    formatMessageContent(content) {
        // Convert markdown-like formatting to HTML
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>')
            .replace(/•/g, '&bull;');
    }
    
    createConfidenceIndicator(confidence, status) {
        const confidenceDiv = document.createElement('div');
        confidenceDiv.className = 'confidence-indicator';
        
        const confidenceText = document.createElement('span');
        const statusEmoji = this.getStatusEmoji(status, confidence);
        
        if (confidence > 80) {
            confidenceText.textContent = `${statusEmoji} High confidence match`;
        } else if (confidence > 50) {
            confidenceText.textContent = `${statusEmoji} Good match`;
        } else if (confidence > 20) {
            confidenceText.textContent = `${statusEmoji} Moderate match`;
        } else {
            confidenceText.textContent = `${statusEmoji} General response`;
        }
        
        const confidenceBar = document.createElement('div');
        confidenceBar.className = 'confidence-bar';
        
        const confidenceFill = document.createElement('div');
        confidenceFill.className = 'confidence-fill';
        confidenceFill.style.width = '0%';
        
        confidenceBar.appendChild(confidenceFill);
        confidenceDiv.appendChild(confidenceText);
        confidenceDiv.appendChild(confidenceBar);
        
        // Animate confidence bar
        setTimeout(() => {
            confidenceFill.style.width = `${Math.min(confidence, 95)}%`;
        }, 300);
        
        return confidenceDiv;
    }
    
    getStatusEmoji(status, confidence) {
        if (status === 'matched' && confidence > 70) return '🎯';
        if (status === 'matched') return '✅';
        if (status === 'fallback') return '💡';
        if (status === 'error') return '⚠️';
        return '🤖';
    }
    
    showTypingIndicator() {
        this.typingIndicator.classList.add('show');
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.typingIndicator.classList.remove('show');
    }
    
    setInputState(enabled) {
        this.userInput.disabled = !enabled;
        this.sendButton.disabled = !enabled;
        
        if (enabled) {
            this.userInput.placeholder = 'Ask me about healthcare...';
            this.sendButton.style.opacity = '1';
        } else {
            this.userInput.placeholder = 'Processing your question...';
            this.sendButton.style.opacity = '0.5';
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    async copyToClipboard(bubble) {
        const text = bubble.textContent.replace('📋 Copied!', '').trim();
        const notification = bubble.querySelector('.copy-notification');
        
        try {
            await navigator.clipboard.writeText(text);
            
            // Show copy notification with enhanced animation
            notification.classList.add('show');
            
            // Hide notification after 2 seconds
            setTimeout(() => {
                notification.classList.remove('show');
            }, 2000);
            
            // Brief status message
            this.showStatusMessage('📋 Copied to clipboard', 'success');
            
        } catch (err) {
            console.error('Failed to copy text:', err);
            // Fallback: create temporary textarea for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                notification.classList.add('show');
                setTimeout(() => notification.classList.remove('show'), 2000);
            } catch (fallbackErr) {
                console.error('Fallback copy failed:', fallbackErr);
            }
            document.body.removeChild(textArea);
        }
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize the chatbot when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new HealthcareChatbot();
});

// Add helpful keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Focus input on '/' key (like Discord)
    if (e.key === '/' && document.activeElement !== document.getElementById('userInput')) {
        e.preventDefault();
        document.getElementById('userInput').focus();
    }
    
    // Toggle theme with Ctrl/Cmd + D
    if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        document.getElementById('themeToggle').click();
    }
    
    // Clear chat with Ctrl/Cmd + L
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        const chatMessages = document.getElementById('chatMessages');
        const messages = chatMessages.querySelectorAll('.message');
        messages.forEach((msg, index) => {
            if (index > 0) { // Keep the welcome message
                setTimeout(() => {
                    msg.style.opacity = '0';
                    msg.style.transform = 'translateY(-20px)';
                    setTimeout(() => msg.remove(), 300);
                }, index * 50);
            }
        });
    }
});

// Add performance monitoring
let performanceStart = Date.now();
window.addEventListener('load', () => {
    const loadTime = Date.now() - performanceStart;
    console.log(`Healthcare Chatbot loaded in ${loadTime}ms`);
});

// Add error handling for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    // Prevent the default browser behavior
    event.preventDefault();
});
