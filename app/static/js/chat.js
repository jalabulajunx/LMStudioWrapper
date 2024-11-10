// app/static/js/chat.js
$(document).ready(function() {
    const chatForm = $('#chat-form');
    const messageInput = $('#message-input');
    const chatMessages = $('.chat-messages');
    const stopButton = $('#stop-button');
    const chatHistory = $('#chat-history');
    let currentConversationId = null;
    let eventSource = null;

    // Conversation Management Functions
    async function loadConversations() {
        try {
            const response = await fetch('/api/conversations');
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
            showNotification('Failed to load conversation history', 'error');
        }
    }

    async function createNewConversation() {
        try {
            const response = await fetch('/api/conversations', {
                method: 'POST'
            });
            const conversation = await response.json();
            currentConversationId = conversation.id;
            chatMessages.empty();
            await loadConversations();
        } catch (error) {
            console.error('Error creating conversation:', error);
            showNotification('Failed to create new conversation', 'error');
            // Fallback to your original UUID generation if API fails
            currentConversationId = crypto.randomUUID();
        }
    }

    // Your existing message handling functions
    function appendMessage(content, role) {
        const messageDiv = $('<div>')
            .addClass('message')
            .addClass(role + '-message');

        if (role === 'assistant') {
            messageDiv.html(marked.parse(content));
        } else {
            messageDiv.text(content);
        }

        chatMessages.append(messageDiv);
        chatMessages.scrollTop(chatMessages[0].scrollHeight);
        return messageDiv;
    }

    // Keep your existing chat submission handler
    chatForm.on('submit', async function(e) {
        e.preventDefault();

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

    // Event Handlers for Conversation Management
    $('#new-chat').on('click', async function() {
        await createNewConversation();
    });

    chatHistory.on('click', '.conversation-item', async function(e) {
        if (!$(e.target).closest('.conversation-actions').length) {
            const convId = $(this).data('conversation-id');
            currentConversationId = convId;
            
            try {
                const response = await fetch(`/api/conversations/${convId}`);
                const messages = await response.json();
                
                chatMessages.empty();
                messages.forEach(msg => {
                    if (msg.content) appendMessage(msg.content, 'user');
                    if (msg.response) appendMessage(msg.response, 'assistant');
                });
                
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

    $('#export-chat').on('click', async function() {
        if (!currentConversationId) {
            showNotification('No conversation to export', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/conversations/${currentConversationId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch conversation data');
            }
            
            const messages = await response.json();
            
            let exportContent = "# Chat Export\n\n";
            exportContent += `Date: ${new Date().toLocaleString()}\n\n`;
            
            messages.forEach(msg => {
                if (msg.content) {
                    exportContent += `**User**: ${msg.content}\n\n`;
                }
                if (msg.response) {
                    exportContent += `**Assistant**: ${msg.response}\n\n`;
                }
            });
            
            // Create and trigger download
            const blob = new Blob([exportContent], { type: 'text/markdown' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `chat-export-${new Date().toISOString().slice(0,10)}.md`;
            
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            setTimeout(() => {
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }, 100);
            
            showNotification('Chat exported successfully', 'success');
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
    createNewConversation();
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