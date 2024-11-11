// app/static/js/chat.js
$(document).ready(function() {

    const chatForm = $('#chat-form');
    const messageInput = $('#message-input');
    const chatMessages = $('.chat-messages');
    const stopButton = $('#stop-button');
    const chatHistory = $('#chat-history');
    let currentConversationId = null;
    let eventSource = null;

    
    // Check authentication first
    const token = sessionStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    // Set up AJAX defaults with token
    $.ajaxSetup({
        beforeSend: function(xhr) {
            xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }
    });

    // Initialize application
    async function initializeApp() {
        try {
            // Fetch user info
            const userResponse = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!userResponse.ok) {
                throw new Error('Failed to fetch user info');
            }
            
            const userData = await userResponse.json();
            
            // Update UI with user info
            $('#username').text(userData.username);
            
            // Update task selector
            if (userData.tasks && Array.isArray(userData.tasks)) {
                const taskSelector = $('#task-selector');
                taskSelector.empty();
                userData.tasks.forEach(task => {
                    const taskName = task.charAt(0).toUpperCase() + task.slice(1);
                    taskSelector.append(`<option value="${task}">${taskName} Chat</option>`);
                });
            }
            
            // If user is admin, show admin UI elements
            if (userData.is_admin) {
                $('.admin-only').removeClass('d-none');
            }
            
            // Load conversations
            await loadConversations();
            await loadLatestConversation();
            
        } catch (error) {
            console.error('Initialization error:', error);
            if (error.message.includes('Failed to fetch user info')) {
                showNotification('Session expired. Please login again.', 'error');
                sessionStorage.removeItem('token');
                window.location.href = '/login';
            } else {
                showNotification('Error initializing application', 'error');
            }
        }
    }

    // Start initialization
    initializeApp().catch(error => {
        console.error('Fatal initialization error:', error);
        showNotification('Failed to initialize application', 'error');
    });

    /* // Fetch user info and initialize
    fetch('/api/auth/me', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to fetch user info');
        return response.json();
    })
    .then(data => {
        $('#username').text(data.username);
        
        // Update task selector if user has specific tasks
        if (data.tasks && Array.isArray(data.tasks)) {
            const taskSelector = $('#task-selector');
            taskSelector.empty();
            data.tasks.forEach(task => {
                taskSelector.append(`<option value="${task}">${task.charAt(0).toUpperCase() + task.slice(1)} Chat</option>`);
            });
        }

        // Now load conversations after successful auth
        return loadConversations();
    })
    .then(() => {
        return loadLatestConversation();
    })
    .catch(error => {
        console.error('Initialization error:', error);
        showNotification('Please log in again', 'error');
        sessionStorage.removeItem('token');
        window.location.href = '/login';
    });
 */
    // Check authentication status
    function checkAuth() {
        const token = sessionStorage.getItem('token');
        if (!token) {
            window.location.href = '/login';
            return false;
        }
        return true;
    }

    // Add more robust error handling for all fetch calls
    function handleFetchError(error, customMessage = 'Operation failed') {
        console.error('Fetch error:', error);
        if (error.message.includes('Failed to fetch')) {
            showNotification('Connection error. Please check your internet connection.', 'error');
        } else if (error.status === 401) {
            showNotification('Session expired. Please login again.', 'error');
            sessionStorage.removeItem('token');
            window.location.href = '/login';
        } else {
            showNotification(customMessage, 'error');
        }
    }

    // Update your existing error handler
    $(document).ajaxError(function(event, jqXHR, settings, thrownError) {
        console.error('AJAX error:', thrownError);
        if (jqXHR.status === 401) {
            showNotification('Session expired. Please login again.', 'error');
            sessionStorage.removeItem('token');
            window.location.href = '/login';
        } else {
            showNotification('An error occurred. Please try again.', 'error');
        }
    });

    // Check auth before proceeding
    if (!checkAuth()) return;

    // Initialize by loading conversations and latest chat
    loadConversations().then(() => {
        loadLatestConversation();
    });

    // Load latest conversation with auth header
    async function loadLatestConversation() {
        try {
            const response = await fetch('/api/conversations', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load conversations');
            }
            
            const conversations = await response.json();
            
            if (conversations && conversations.length > 0) {
                const latestConv = conversations[0];
                currentConversationId = latestConv.id;
                
                const msgResponse = await fetch(`/api/conversations/${latestConv.id}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (!msgResponse.ok) {
                    throw new Error('Failed to load conversation messages');
                }
                
                const data = await msgResponse.json();
                
                if (data.messages && Array.isArray(data.messages)) {
                    chatMessages.empty();
                    data.messages.forEach(msg => {
                        if (msg.content) appendMessage(msg.content, 'user');
                        if (msg.response) appendMessage(msg.response, 'assistant');
                    });
                }
            }
        } catch (error) {
            console.error('Error loading latest conversation:', error);
            if (error.status === 401) {
                showNotification('Session expired. Please login again.', 'error');
                sessionStorage.removeItem('token');
                window.location.href = '/login';
            } else {
                showNotification('Failed to load conversation', 'error');
            }
        }
    }

    // Load conversations with auth header
    async function loadConversations() {
        try {
            const response = await fetch('/api/conversations', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load conversations');
            }
            
            const conversations = await response.json();
            
            chatHistory.empty();
            conversations.forEach(conv => {
                const convDiv = $('<div>')
                    .addClass('conversation-item p-3 border-bottom cursor-pointer')
                    .attr('data-conversation-id', conv.id)
                    .html(`
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="conversation-title text-truncate">${conv.title}</div>
                            <div class="conversation-actions">
                                <button class="btn btn-sm btn-outline-secondary rename-conv">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger delete-conv">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="text-muted small text-truncate">${conv.last_message || ''}</div>
                    `);
                
                if (conv.id === currentConversationId) {
                    convDiv.addClass('active');
                }
                
                chatHistory.append(convDiv);
            });
        } catch (error) {
            console.error('Error loading conversations:', error);
            if (error.status === 401) {
                showNotification('Session expired. Please login again.', 'error');
                sessionStorage.removeItem('token');
                window.location.href = '/login';
            } else {
                showNotification('Failed to load conversations', 'error');
            }
        }
    }

    async function createNewConversation() {
        try {
            const response = await fetch('/api/conversations', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${sessionStorage.getItem('token')}`
                }
            });
            const conversation = await response.json();
            currentConversationId = conversation.id;
            chatMessages.empty();
            await loadConversations();
        } catch (error) {
            console.error('Error creating conversation:', error);
            showNotification('Failed to create new conversation', 'error');
            currentConversationId = crypto.randomUUID();
        }
    }

    // Append message
    function appendMessage(content, role) {
        const messageDiv = $('<div>')
            .addClass('message')
            .addClass(role + '-message');
        
        const contentDiv = $('<div>').addClass('message-content');
        
        if (role === 'assistant') {
            contentDiv.html(marked.parse(content));
        } else {
            contentDiv.text(content);
        }
        
        messageDiv.append(contentDiv);
        chatMessages.append(messageDiv);
        chatMessages.scrollTop(chatMessages[0].scrollHeight);
        return messageDiv;
    }

    // Keep your existing chat submission handler
    chatForm.on('submit', async function(e) {
        e.preventDefault();
        if (!checkAuth()) return;

        const message = messageInput.val().trim();
        if (!message) return;

        if (!currentConversationId) {
            await createNewConversation();
        }

        appendMessage(message, 'user');
        messageInput.val('');
        stopButton.removeClass('d-none');

        const responseDiv = appendMessage('', 'assistant');
        let fullResponse = '';

        if (eventSource) {
            eventSource.close();
        }

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: currentConversationId
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const {value, done} = await reader.read();
                if (done) break;

                const text = decoder.decode(value);
                const lines = text.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(5).trim();

                        if (data === '[DONE]') {
                            stopButton.addClass('d-none');
                            await loadConversations(); // Refresh conversation list
                            break;
                        }

                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.error) {
                                responseDiv.html(marked.parse('Error: ' + parsed.error));
                                stopButton.addClass('d-none');
                                break;
                            }

                            if (parsed.token) {
                                fullResponse += parsed.token;
                                responseDiv.html(marked.parse(fullResponse));
                                chatMessages.scrollTop(chatMessages[0].scrollHeight);
                            }
                        } catch (error) {
                            console.error('Error parsing SSE data:', error);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Request error:', error);
            responseDiv.html(marked.parse('Error: Failed to generate response'));
            stopButton.addClass('d-none');
        }
    });

    // Add logout button and handler
    $('.navbar-nav').append(`
        <li class="nav-item">
            <button class="btn btn-outline-danger ms-2" id="logout-button">
                <i class="bi bi-box-arrow-right"></i> Logout
            </button>
        </li>
    `);

    // Add logout handler
    $('#logout-button').on('click', function() {
        if (confirm('Are you sure you want to logout?')) {
            sessionStorage.removeItem('token');
            showNotification('Logged out successfully', 'success');
            setTimeout(() => {
                window.location.href = '/login';
            }, 500);
        }
    });

    // Event Handlers for Conversation Management
    $('#new-chat').on('click', async function() {
        try {
            await createNewConversation();
            chatMessages.empty();  // Clear the chat area
            messageInput.focus();  // Focus on input for better UX
        } catch (error) {
            console.error('Error creating new conversation:', error);
            showNotification('Failed to create new conversation', 'error');
        }
    });

    chatHistory.on('click', '.conversation-item', async function(e) {
        if (!$(e.target).closest('.conversation-actions').length) {
            const convId = $(this).data('conversation-id');
            currentConversationId = convId;
            
            try {
                const response = await fetch(`/api/conversations/${convId}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                
                // Clear existing messages
                chatMessages.empty();
                
                // Check if we have messages and they're in an array
                if (data.messages && Array.isArray(data.messages)) {
                    data.messages.forEach(msg => {
                        if (msg.content) appendMessage(msg.content, 'user');
                        if (msg.response) appendMessage(msg.response, 'assistant');
                    });
                }
                
                $('.conversation-item').removeClass('active');
                $(this).addClass('active');
            } catch (error) {
                console.error('Error loading conversation:', error);
                showNotification('Failed to load conversation messages', 'error');
            }
        }
    });

    // Rename conversation handler
    chatHistory.on('click', '.rename-conv', async function(e) {
        e.stopPropagation();  // Prevent triggering conversation click
        const convItem = $(this).closest('.conversation-item');
        const convId = convItem.data('conversation-id');
        const titleElement = convItem.find('.conversation-title');
        const currentTitle = titleElement.text().trim();
        
        const newTitle = prompt('Enter new conversation title:', currentTitle);
        if (newTitle && newTitle !== currentTitle) {
            try {
                const response = await fetch(`/api/conversations/${convId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ title: newTitle })
                });

                if (!response.ok) {
                    throw new Error('Failed to rename conversation');
                }

                await loadConversations();  // Refresh the conversation list
                showNotification('Conversation renamed successfully', 'success');
            } catch (error) {
                console.error('Error renaming conversation:', error);
                showNotification('Failed to rename conversation', 'error');
            }
        }
    });

    // Delete conversation handler
    chatHistory.on('click', '.delete-conv', async function(e) {
        e.stopPropagation();  // Prevent triggering conversation click
        
        const convItem = $(this).closest('.conversation-item');
        const convId = convItem.data('conversation-id');
        const isCurrentConv = convId === currentConversationId;
        
        if (!confirm('Are you sure you want to delete this conversation?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/conversations/${convId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete conversation');
            }

            if (isCurrentConv) {
                // If we deleted the current conversation, create a new one
                await createNewConversation();
            } else {
                // Otherwise just refresh the list
                await loadConversations();
            }
            
            showNotification('Conversation deleted successfully', 'success');
        } catch (error) {
            console.error('Error deleting conversation:', error);
            showNotification('Failed to delete conversation', 'error');
        }
    });

    // Keep your existing stop button handler
    stopButton.on('click', function() {
        if (eventSource) {
            eventSource.close();
            stopButton.addClass('d-none');
        }
    });

    // Keep your existing enter to send handler
    messageInput.on('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.submit();
        }
    });

    // Add search functionality
    $('#search-conversations').on('input', function() {
        const searchTerm = $(this).val().toLowerCase();
        $('.conversation-item').each(function() {
            const title = $(this).find('.conversation-title').text().toLowerCase();
            const lastMessage = $(this).find('.text-muted').text().toLowerCase();
            const matches = title.includes(searchTerm) || lastMessage.includes(searchTerm);
            $(this).toggle(matches);
        });
    });

    //Copy conversation to clipboard handler
    $('#copy-conversation').on('click', async function() {
        if (!currentConversationId) {
            showNotification('No conversation to copy', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/conversations/${currentConversationId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Create Copy Content in same format as export
            let copyContent = "# Chat Conversation\n\n";
            copyContent += `Date: ${new Date().toLocaleString()}\n`;
            
            if (data.conversation && data.conversation.title) {
                copyContent += `Title: ${data.conversation.title}\n`;
            }
            copyContent += "\n---\n\n";
            
            if (data.messages && Array.isArray(data.messages)) {
                data.messages.forEach(msg => {
                    const timestamp = new Date(msg.timestamp).toLocaleString();
                    if (msg.content) {
                        copyContent += `### User (${timestamp}):\n${msg.content}\n\n`;
                    }
                    if (msg.response) {
                        copyContent += `### Assistant:\n${msg.response}\n\n`;
                    }
                    copyContent += "---\n\n";
                });
                
                // Copy to clipboard
                navigator.clipboard.writeText(copyContent)
                    .then(() => {
                        const $btn = $(this);
                        const originalHtml = $btn.html();
                        
                        // Visual feedback
                        $btn.html('<i class="bi bi-clipboard-check"></i> Copied!')
                            .addClass('btn-success')
                            .removeClass('btn-outline-secondary');
                        
                        showNotification('Conversation copied to clipboard', 'success');
                        
                        // Reset button after delay
                        setTimeout(() => {
                            $btn.html(originalHtml)
                                .removeClass('btn-success')
                                .addClass('btn-outline-secondary');
                        }, 2000);
                    })
                    .catch(error => {
                        console.error('Error copying text:', error);
                        showNotification('Failed to copy conversation', 'error');
                    });
            } else {
                throw new Error('No messages found in conversation');
            }
        } catch (error) {
            console.error('Error copying chat:', error);
            showNotification('Failed to copy chat', 'error');
        }
    });

    //Export chat event handler
    $('#export-chat').on('click', async function() {
        if (!currentConversationId) {
            showNotification('No conversation to export', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/conversations/${currentConversationId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Create Export Content
            let exportContent = "# Chat Export\n\n";
            exportContent += `Date: ${new Date().toLocaleString()}\n`;
            
            if (data.conversation && data.conversation.title) {
                exportContent += `Title: ${data.conversation.title}\n`;
            }
            exportContent += "\n---\n\n";
            
            if (data.messages && Array.isArray(data.messages)) {
                data.messages.forEach(msg => {
                    const timestamp = new Date(msg.timestamp).toLocaleString();
                    if (msg.content) {
                        exportContent += `### User (${timestamp}):\n${msg.content}\n\n`;
                    }
                    if (msg.response) {
                        exportContent += `### Assistant:\n${msg.response}\n\n`;
                    }
                    exportContent += "---\n\n";
                });
                
                // Create and trigger download
                const blob = new Blob([exportContent], { type: 'text/markdown' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                const fileName = data.conversation?.title 
                    ? `${data.conversation.title}-${new Date().toISOString().slice(0,10)}.md`
                    : `chat-export-${new Date().toISOString().slice(0,10)}.md`;
                a.download = fileName;
                
                document.body.appendChild(a);
                a.click();
                
                // Cleanup
                setTimeout(() => {
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                }, 100);
                
                showNotification('Chat exported successfully', 'success');
            } else {
                throw new Error('No messages found in conversation');
            }
        } catch (error) {
            console.error('Error exporting chat:', error);
            showNotification('Failed to export chat', 'error');
        }
    });

    // Task selector handling
    $('#task-selector').on('change', function() {
        const selectedTask = $(this).val();
        // We'll implement this fully when we add authentication
        // For now, just store the selection
        localStorage.setItem('selectedTask', selectedTask);
    });
    

    // Initialize
    //createNewConversation();
    loadConversations();

    // Notification helper
    function showNotification(message, type = 'info') {
        const toast = $('#notification-toast');
        toast.find('.toast-body').text(message);
        toast.removeClass('bg-success bg-danger bg-info')
             .addClass(`bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'}`);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
});