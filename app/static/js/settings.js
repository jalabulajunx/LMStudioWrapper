// app/static/js/settings.js
$(document).ready(function() {
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

    // Initialize theme
    const isDark = localStorage.getItem('theme') === 'dark';
    $('#theme-switch').prop('checked', isDark);

    // Theme switch handler
    $('#theme-switch').on('change', function() {
        const isDark = $(this).is(':checked');
        window.themeUtils.setTheme(isDark);
    });

    // Initialize by loading user info and models
    async function initialize() {
        try {
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch user info');
            }

            const userData = await response.json();
            $('#username').text(userData.username);

            // Show admin menu if user is admin
            if (userData.is_admin) {
                $('#admin-menu').removeClass('d-none');
            }

            // Load available models
            await loadModels();
        } catch (error) {
            console.error('Initialization error:', error);
            if (error.message === 'Authentication expired') {
                sessionStorage.removeItem('token');
                window.location.href = '/login';
            } else {
                showNotification('Error initializing settings', 'error');
            }
        }
    }

    // Load available models
    async function loadModels() {
        try {
            const response = await fetch('/api/settings/models');
            if (!response.ok) {
                throw new Error('Failed to fetch models');
            }
            
            const models = await response.json();
            const modelSelector = $('#model-selector');
            modelSelector.empty();
            
            models.forEach(model => {
                modelSelector.append(
                    `<option value="${model.id}">${model.name}</option>`
                );
            });
            
            // Set current model if stored
            const savedModel = localStorage.getItem('selectedModel');
            if (savedModel) {
                modelSelector.val(savedModel);
            }
            
        } catch (error) {
            console.error('Error loading models:', error);
            showNotification('Failed to load available models', 'error');
        }
    }

    // Theme handling
    function initializeTheme() {
        const isDark = localStorage.getItem('theme') === 'dark';
        $('#theme-switch').prop('checked', isDark);
        setTheme(isDark);
    }

    function setTheme(isDark) {
        document.documentElement.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }

    // Event handlers
    $('#theme-switch').on('change', function() {
        const isDark = $(this).is(':checked');
        setTheme(isDark);
    });

    $('#model-selector').on('change', function() {
        const selectedModel = $(this).val();
        localStorage.setItem('selectedModel', selectedModel);
        showNotification('Model preference saved', 'success');
    });

    $('#refresh-models').on('click', async function() {
        try {
            await loadModels();
            showNotification('Models refreshed successfully', 'success');
        } catch (error) {
            showNotification('Failed to refresh models', 'error');
        }
    });

    $('#notifications-switch').on('change', function() {
        const enabled = $(this).is(':checked');
        localStorage.setItem('notifications', enabled ? 'enabled' : 'disabled');
        showNotification(
            `Notifications ${enabled ? 'enabled' : 'disabled'}`,
            'success'
        );
    });

    // Logout handler
    $('#logout-button').on('click', function() {
        if (confirm('Are you sure you want to logout?')) {
            sessionStorage.removeItem('token');
            showNotification('Logged out successfully', 'success');
            setTimeout(() => {
                window.location.href = '/login';
            }, 500);
        }
    });

    // Error handler
    function handleError(error) {
        console.error('Error:', error);
        if (error.status === 401) {
            showNotification('Session expired. Please login again.', 'error');
            sessionStorage.removeItem('token');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1000);
        } else {
            showNotification(error.message || 'An error occurred', 'error');
        }
    }

    // Notification helper
    function showNotification(message, type = 'info') {
        const toast = $('#notification-toast');
        toast.find('.toast-body').text(message);
        toast.removeClass('bg-success bg-danger bg-info')
            .addClass(`bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'}`);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    // Start initialization
    initialize();
});