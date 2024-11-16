// app/static/js/notifications.js

class NotificationManager {
    constructor() {
        this.container = this.createContainer();
        this.notifications = new Map();
        this.counter = 0;
    }

    createContainer() {
        const container = document.createElement('div');
        container.className = 'notifications-container';
        document.body.appendChild(container);
        return container;
    }

    show(message, type = 'info', duration = 5000) {
        const id = `notification-${++this.counter}`;
        const notification = this.createNotification(id, message, type);
        
        this.notifications.set(id, notification);
        this.container.appendChild(notification);
        
        // Trigger animation
        setTimeout(() => notification.classList.add('show'), 10);
        
        if (duration) {
            setTimeout(() => this.dismiss(id), duration);
        }
        
        return id;
    }

    createNotification(id, message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.id = id;
        
        notification.innerHTML = `
            <div class="notification-header">
                <span class="notification-title">
                    ${type === 'success' ? '<i class="bi bi-check-circle"></i>' :
                      type === 'error' ? '<i class="bi bi-exclamation-circle"></i>' :
                      type === 'warning' ? '<i class="bi bi-exclamation-triangle"></i>' :
                      '<i class="bi bi-info-circle"></i>'}
                    ${type.charAt(0).toUpperCase() + type.slice(1)}
                </span>
                <button class="notification-close" aria-label="Close">
                    <i class="bi bi-x"></i>
                </button>
            </div>
            <div class="notification-body">
                <div class="notification-message">${message}</div>
            </div>
        `;
        
        notification.querySelector('.notification-close').addEventListener(
            'click', 
            () => this.dismiss(id)
        );
        
        return notification;
    }

    showProgress(files) {
        const id = `notification-${++this.counter}`;
        const notification = document.createElement('div');
        notification.className = 'notification notification-info';
        notification.id = id;
        
        const totalSize = files.reduce((sum, file) => sum + file.size, 0);
        
        notification.innerHTML = `
            <div class="notification-header">
                <span class="notification-title">
                    <i class="bi bi-cloud-upload"></i> Uploading Files
                </span>
                <button class="notification-close" aria-label="Close">
                    <i class="bi bi-x"></i>
                </button>
            </div>
            <div class="notification-body">
                <div class="notification-message">
                    Uploading ${files.length} file${files.length > 1 ? 's' : ''}
                </div>
                <div class="notification-progress">
                    <div class="progress">
                        <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                    </div>
                    <div class="progress-text small text-muted">0%</div>
                </div>
                <div class="notification-files">
                    ${files.map(file => `
                        <div class="notification-file" data-file-name="${file.name}">
                            <span class="notification-file-name">${file.name}</span>
                            <span class="notification-file-progress">Waiting...</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        notification.querySelector('.notification-close').addEventListener(
            'click', 
            () => this.dismiss(id)
        );
        
        this.notifications.set(id, notification);
        this.container.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 10);
        
        return {
            id,
            updateProgress: (fileName, progress) => {
                const fileEl = notification.querySelector(`[data-file-name="${fileName}"]`);
                if (fileEl) {
                    fileEl.querySelector('.notification-file-progress').textContent = 
                        `${Math.round(progress)}%`;
                }
                
                // Update overall progress
                const files = notification.querySelectorAll('.notification-file');
                const totalProgress = Array.from(files).reduce((sum, file) => {
                    const progress = parseInt(file.querySelector('.notification-file-progress').textContent);
                    return sum + (isNaN(progress) ? 0 : progress);
                }, 0) / files.length;
                
                notification.querySelector('.progress-bar').style.width = `${totalProgress}%`;
                notification.querySelector('.progress-text').textContent = 
                    `${Math.round(totalProgress)}%`;
                
                return totalProgress === 100;
            },
            complete: () => {
                notification.classList.remove('notification-info');
                notification.classList.add('notification-success');
                notification.querySelector('.notification-title').innerHTML = 
                    '<i class="bi bi-check-circle"></i> Upload Complete';
                notification.querySelector('.progress-bar').classList.add('bg-success');
                setTimeout(() => this.dismiss(id), 3000);
            },
            error: (error) => {
                notification.classList.remove('notification-info');
                notification.classList.add('notification-error');
                notification.querySelector('.notification-title').innerHTML = 
                    '<i class="bi bi-exclamation-circle"></i> Upload Failed';
                notification.querySelector('.notification-message').textContent = error;
                notification.querySelector('.progress-bar').classList.add('bg-danger');
                // Don't auto-dismiss error notifications
            }
        };
    }

    dismiss(id) {
        const notification = this.notifications.get(id);
        if (notification) {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
                this.notifications.delete(id);
            }, 300);
        }
    }
}

// Create global instance
window.notificationManager = new NotificationManager();