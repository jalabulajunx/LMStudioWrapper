// app/static/js/admin.js
$(document).ready(function() {
        
    let currentPage = 1;
    const pageSize = 10;
    let totalPages = 1;
    const userModal = new bootstrap.Modal('#userModal');
    const token = sessionStorage.getItem('token');
    let editingUserId = null;

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

    $('#users-table').after(`
        <div class="d-flex justify-content-between align-items-center mt-3">
            <div class="d-flex align-items-center">
                <span class="me-2">Page Size:</span>
                <select class="form-select form-select-sm" id="page-size" style="width: auto;">
                    <option value="10">10</option>
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                </select>
            </div>
            <div>
                <nav aria-label="User list pagination">
                    <ul class="pagination mb-0">
                        <li class="page-item">
                            <button class="page-link" id="prev-page">
                                <i class="bi bi-chevron-left"></i>
                            </button>
                        </li>
                        <li class="page-item">
                            <span class="page-link" id="page-info">
                                Page <span id="current-page">1</span>
                                of <span id="total-pages">1</span>
                            </span>
                        </li>
                        <li class="page-item">
                            <button class="page-link" id="next-page">
                                <i class="bi bi-chevron-right"></i>
                            </button>
                        </li>
                    </ul>
                </nav>
            </div>
        </div>
    `);


    // Initialize theme when modal is shown
    userModal._element.addEventListener('show.bs.modal', function () {
        const isDark = localStorage.getItem('theme') === 'dark';
        $(this).find('.modal-content').attr('data-bs-theme', isDark ? 'dark' : 'light');
    });

    // Watch for theme changes
    $(window).on('storage', function(e) {
        if (e.originalEvent.key === 'theme') {
            updateThemeToggleText();
        }
    });

    // Initialize by loading user info and data
    async function initialize() {
        try {
            // Check auth and admin status
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Authentication expired');
                }
                throw new Error('Failed to fetch user info');
            }

            const userData = await response.json();
            if (!userData.is_admin) {
                window.location.href = '/';
                return;
            }

            $('#username').text(userData.username);

            // Load roles and tasks
            await loadRolesAndTasks();
            // Load user list
            await loadUsers();

            // Update theme toggle text
            updateThemeToggleText();

        } catch (error) {
            console.error('Initialization error:', error);
            if (error.message === 'Authentication expired') {
                sessionStorage.removeItem('token');
                window.location.href = '/login';
            } else {
                showNotification('Error initializing admin panel', 'error');
            }
        }
    }

    // Load roles and tasks for the form
    async function loadRolesAndTasks() {
        try {
            const [rolesResponse, tasksResponse] = await Promise.all([
                fetch('/api/admin/roles', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }),
                fetch('/api/admin/tasks', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })
            ]);

            if (!rolesResponse.ok || !tasksResponse.ok) {
                throw new Error('Failed to load roles or tasks');
            }

            const roles = await rolesResponse.json();
            const tasks = await tasksResponse.json();

            // Populate roles checkboxes
            const rolesDiv = $('#roles-checkboxes');
            rolesDiv.empty();
            roles.forEach(role => {
                rolesDiv.append(`
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" 
                               id="role-${role.id}" value="${role.id}">
                        <label class="form-check-label" for="role-${role.id}">
                            ${role.name}
                        </label>
                    </div>
                `);
            });

            // Populate tasks checkboxes
            const tasksDiv = $('#tasks-checkboxes');
            tasksDiv.empty();
            tasks.forEach(task => {
                tasksDiv.append(`
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" 
                               id="task-${task.id}" value="${task.id}">
                        <label class="form-check-label" for="task-${task.id}">
                            ${task.name}
                        </label>
                    </div>
                `);
            });
        } catch (error) {
            console.error('Error loading roles and tasks:', error);
            showNotification('Failed to load roles and tasks', 'error');
        }
    }

    // Load users table with error handling
    async function loadUsers(page = 1, pageSize = 10, search = '') {
        try {
            const queryParams = new URLSearchParams({
                page: page,
                page_size: pageSize,
                ...(search && { search: search })
            });

            const response = await fetch(`/api/admin/users?${queryParams}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load users');
            }

            const data = await response.json();
            currentPage = data.page;
            totalPages = data.total_pages;

            // Update pagination UI
            $('#current-page').text(currentPage);
            $('#total-pages').text(totalPages);
            $('#prev-page').prop('disabled', currentPage <= 1);
            $('#next-page').prop('disabled', currentPage >= totalPages);

            const tbody = $('#users-table tbody');
            tbody.empty();

            data.items.forEach(user => {
                const row = $(`
                    <tr>
                        <td>${user.username}</td>
                        <td>${user.full_name}</td>
                        <td>${user.email}</td>
                        <td>
                            <span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">
                                ${user.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </td>
                        <td>${Array.isArray(user.roles) ? user.roles.join(', ') : ''}</td>
                        <td>${Array.isArray(user.tasks) ? user.tasks.join(', ') : ''}</td>
                        <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td>
                        <td>
                            <div class="btn-group">
                                <button class="btn btn-sm btn-outline-primary edit-user" 
                                        data-id="${user.id}" title="Edit user">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                ${user.username !== 'admin' ? `
                                    <button class="btn btn-sm btn-outline-danger delete-user" 
                                            data-id="${user.id}" title="Delete user">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `);
                tbody.append(row);
            });
        } catch (error) {
            console.error('Error loading users:', error);
            showNotification('Failed to load users', 'error');
        }
    }

    // Add pagination event handlers
    $('#prev-page').on('click', function() {
        if (currentPage > 1) {
            loadUsers(currentPage - 1, pageSize);
        }
    });

    $('#next-page').on('click', function() {
        if (currentPage < totalPages) {
            loadUsers(currentPage + 1, pageSize);
        }
    });

    $('#page-size').on('change', function() {
        pageSize = parseInt($(this).val());
        currentPage = 1;  // Reset to first page when changing page size
        loadUsers(currentPage, pageSize);
    });

    // Add search functionality
    let searchTimeout;
    $('#search-users').on('input', function() {
        clearTimeout(searchTimeout);
        const searchTerm = $(this).val().trim();
        
        searchTimeout = setTimeout(() => {
            currentPage = 1;  // Reset to first page when searching
            loadUsers(currentPage, pageSize, searchTerm);
        }, 300);  // Debounce search
    });

    // Create/Edit User form submit
    $('#save-user-btn').on('click', async function() {
        try {
            // Validate form
            const form = $('#user-form')[0];
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
    
            const userData = {
                username: $('#username-input').val().trim(),
                full_name: $('#fullname-input').val().trim(),
                email: $('#email-input').val().trim(),
                is_active: $('#is-active').is(':checked'),
                roles: $('.form-check-input[id^="role-"]:checked').map(function() {
                    return $(this).val();
                }).get(),
                tasks: $('.form-check-input[id^="task-"]:checked').map(function() {
                    return $(this).val();
                }).get()
            };
    
            // Add password only if it's provided (for edit)
            const password = $('#password-input').val().trim();
            if (password) {
                userData.password = password;
            }
    
            const url = editingUserId ? 
                `/api/admin/users/${editingUserId}` : 
                '/api/admin/users';
            
            const method = editingUserId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`  // Add token to request
                },
                body: JSON.stringify(userData)
            });
    
            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Authentication expired');
                }
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save user');
            }
    
            showNotification(
                `User ${editingUserId ? 'updated' : 'created'} successfully`, 
                'success'
            );
            userModal.hide();
            await loadUsers();  // Refresh the user list
        } catch (error) {
            console.error('Error saving user:', error);
            if (error.message === 'Authentication expired') {
                sessionStorage.removeItem('token');
                window.location.href = '/login';
            } else {
                showNotification(error.message || 'Failed to save user', 'error');
            }
        }
    });
    

    // Create new user button
    $('#create-user-btn').on('click', function() {
        editingUserId = null;
        $('#userModalLabel').text('Create User');
        $('#user-form')[0].reset();
        $('#password-input').prop('required', true);
        $('#password-help').text('Password is required for new users');
        userModal.show();
    });

    // Edit user button
    $(document).on('click', '.edit-user', async function() {
        editingUserId = $(this).data('id');
        try {
            const response = await fetch(`/api/admin/users/${editingUserId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`  // Add token to request
                }
            });
    
            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Authentication expired');
                }
                throw new Error('Failed to load user details');
            }
    
            const user = await response.json();
    
            $('#userModalLabel').text('Edit User');
            $('#username-input').val(user.username);
            $('#fullname-input').val(user.full_name);
            $('#email-input').val(user.email);
            $('#password-input').val('').prop('required', false);
            $('#password-help').text('Leave blank to keep existing password');
            $('#is-active').prop('checked', user.is_active);
    
            // Clear existing role selections
            $('input[id^="role-"]').prop('checked', false);
            if (Array.isArray(user.roles)) {
                user.roles.forEach(roleName => {
                    $(`input[id^="role-"]`).each(function() {
                        const roleLabel = $(this).next('label').text().trim();
                        if (roleLabel === roleName) {
                            $(this).prop('checked', true);
                        }
                    });
                });
            }
    
            // Clear existing task selections
            $('input[id^="task-"]').prop('checked', false);
            if (Array.isArray(user.tasks)) {
                user.tasks.forEach(taskName => {
                    $(`input[id^="task-"]`).each(function() {
                        const taskLabel = $(this).next('label').text().trim();
                        if (taskLabel === taskName) {
                            $(this).prop('checked', true);
                        }
                    });
                });
            }
    
            userModal.show();
        } catch (error) {
            console.error('Error loading user:', error);
            if (error.message === 'Authentication expired') {
                sessionStorage.removeItem('token');
                window.location.href = '/login';
            } else {
                showNotification('Failed to load user details', 'error');
            }
        }
    });

    // Delete user button
    $(document).on('click', '.delete-user', async function() {
        const userId = $(this).data('id');
        const username = $(this).closest('tr').find('td:first').text();
        
        if (confirm(`Are you sure you want to delete user "${username}"?`)) {
            try {
                const response = await fetch(`/api/admin/users/${userId}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error('Failed to delete user');
                }

                showNotification('User deleted successfully', 'success');
                await loadUsers();
            } catch (error) {
                console.error('Error deleting user:', error);
                showNotification('Failed to delete user', 'error');
            }
        }
    });

    // Theme toggle handler
    $('#toggle-theme').on('click', function(e) {
        e.preventDefault();
        const currentTheme = localStorage.getItem('theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        window.themeUtils.setTheme(newTheme === 'dark');
        
        // Update icon and text
        const $toggle = $(this);
        if (newTheme === 'dark') {
            $toggle.html('<i class="bi bi-sun"></i> Light Mode');
        } else {
            $toggle.html('<i class="bi bi-moon"></i> Dark Mode');
        }
    });

    // Update theme toggle text on load
    function updateThemeToggleText() {
        const isDark = localStorage.getItem('theme') === 'dark';
        const $toggle = $('#toggle-theme');
        if (isDark) {
            $toggle.html('<i class="bi bi-sun"></i> Light Mode');
        } else {
            $toggle.html('<i class="bi bi-moon"></i> Dark Mode');
        }
    }

    // Password visibility toggle
    $('#toggle-password').on('click', function() {
        const passwordInput = $('#password-input');
        const type = passwordInput.attr('type') === 'password' ? 'text' : 'password';
        passwordInput.attr('type', type);
        $(this).find('i').toggleClass('bi-eye bi-eye-slash');
    });

    // Logout button
    $('#logout-button').on('click', function() {
        if (confirm('Are you sure you want to logout?')) {
            sessionStorage.removeItem('token');
            showNotification('Logged out successfully', 'success');
            setTimeout(() => {
                window.location.href = '/login';
            }, 500);
        }
    });

    // Error handler function
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

    // Show notification helper
    function showNotification(message, type = 'info') {
        const toast = $('#notification-toast');
        toast.find('.toast-body').text(message);
        toast.removeClass('bg-success bg-danger bg-info')
            .addClass(`bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'}`);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    // Initialize the application
    initialize();
});