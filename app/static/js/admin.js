// app/static/js/admin.js
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

    const userModal = new bootstrap.Modal('#userModal');
    let editingUserId = null;

    // Initialize by loading user info and data
    async function initialize() {
        try {
            // Check if user is admin
            const userResponse = await fetch('/api/auth/me');
            const userData = await userResponse.json();
            
            if (!userData.is_admin) {
                showNotification('Unauthorized access', 'error');
                window.location.href = '/';
                return;
            }

            $('#username').text(userData.username);
            
            // Load roles and tasks
            await loadRolesAndTasks();
            // Load user list
            await loadUsers();
        } catch (error) {
            console.error('Initialization error:', error);
            handleError(error);
        }
    }

    // Load roles and tasks for the form
    async function loadRolesAndTasks() {
        try {
            const [rolesResponse, tasksResponse] = await Promise.all([
                fetch('/api/admin/roles'),
                fetch('/api/admin/tasks')
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

    // Load users table
    async function loadUsers() {
        try {
            const response = await fetch('/api/admin/users');
            if (!response.ok) {
                throw new Error('Failed to load users');
            }
            const users = await response.json();

            const tbody = $('#users-table tbody');
            tbody.empty();

            users.forEach(user => {
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
                        <td>${user.roles.join(', ')}</td>
                        <td>${user.tasks.join(', ')}</td>
                        <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td>
                        <td>
                            <div class="btn-group">
                                <button class="btn btn-sm btn-outline-primary edit-user" 
                                        data-id="${user.id}" title="Edit user">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                ${user.id !== 'admin' ? `
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

            // Add password only if it's provided or it's a new user
            const password = $('#password-input').val().trim();
            if (password || !editingUserId) {
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
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save user');
            }

            showNotification(
                `User ${editingUserId ? 'updated' : 'created'} successfully`, 
                'success'
            );
            userModal.hide();
            await loadUsers();
        } catch (error) {
            console.error('Error saving user:', error);
            showNotification(error.message || 'Failed to save user', 'error');
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
            const response = await fetch(`/api/admin/users/${editingUserId}`);
            if (!response.ok) {
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

            // Set roles
            $('input[id^="role-"]').prop('checked', false);
            user.roles.forEach(roleId => {
                $(`#role-${roleId}`).prop('checked', true);
            });

            // Set tasks
            $('input[id^="task-"]').prop('checked', false);
            user.tasks.forEach(taskId => {
                $(`#task-${taskId}`).prop('checked', true);
            });

            userModal.show();
        } catch (error) {
            console.error('Error loading user:', error);
            showNotification('Failed to load user details', 'error');
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