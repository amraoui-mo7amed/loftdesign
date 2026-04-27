/**
 * Notification handler using django-eventstream
 * Connects to user-specific channel and handles real-time notifications
 */

(function() {
    'use strict';

    const NotificationHandler = {
        eventSource: null,
        channel: null,
        reconnectInterval: 5000,
        reconnectAttempts: 0,
        maxReconnectAttempts: 10,
        userId: null,
        urls: {},
        msgs: {},

        /**
         * Initialize notification handler
         */
        init: function() {
            const container = document.getElementById('dashboard-container');
            if (!container) {
                console.warn('NotificationHandler: Dashboard container not found');
                return;
            }

            const ds = container.dataset;
            this.userId = ds.userId;
            
            if (!this.userId || ds.isAuthenticated !== 'True') {
                return;
            }

            // Load Config from data attributes
            this.urls = {
                stream: ds.urlStream || '/events/',
                unreadCount: ds.urlUnreadCount,
                list: ds.urlList,
                markReadBase: ds.urlMarkReadBase, // Should be /dashboard/notifications/
                markAllRead: ds.urlMarkAllRead
            };

            this.msgs = {
                justNow: ds.msgJustNow,
                minutesAgo: ds.msgMinutesAgo,
                hoursAgo: ds.msgHoursAgo,
                empty: ds.msgEmpty,
                new: ds.msgNew
            };

            this.channel = `user-${this.userId}`;
            
            this.connect();
            this.loadUnreadCount();
            this.reloadNotifications();
            this.setupMarkAllRead();
        },

        /**
         * Connect to EventStream endpoint
         */
        connect: function() {
            if (this.eventSource) {
                this.eventSource.close();
            }

            const url = `${this.urls.stream}?channel=${this.channel}`;
            
            if (typeof ReconnectingEventSource !== 'undefined') {
                this.eventSource = new ReconnectingEventSource(url);
            } else {
                this.eventSource = new EventSource(url);
            }

            this.eventSource.onopen = () => {
                this.reconnectAttempts = 0;
            };

            const eventHandler = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    this.handleNotification(data);
                } catch (err) {
                    console.error('NotificationHandler: Error parsing data:', err);
                }
            };

            this.eventSource.addEventListener('message', eventHandler);
            this.eventSource.addEventListener('notification', eventHandler);

            this.eventSource.onerror = (e) => {
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    setTimeout(() => this.connect(), this.reconnectInterval);
                }
            };

            this.eventSource.addEventListener('stream-reset', () => {
                this.reloadNotifications();
            });
        },

        handleNotification: function(data) {
            this.incrementUnreadCount();
            this.showToast(data);
            this.prependNotificationToList(data);
            
            // Trigger bell animation if exists
            const bell = document.querySelector('.notifications-icon');
            if (bell) {
                bell.classList.remove('has-unread');
                void bell.offsetWidth; // Trigger reflow
                bell.classList.add('has-unread');
            }
        },

        showToast: function(notification) {
            const iconMap = {
                'success': 'check-circle',
                'error': 'exclamation-circle',
                'warning': 'exclamation-triangle',
                'info': 'info-circle'
            };
            
            const icon = iconMap[notification.type] || 'bell';
            const toast = document.createElement('div');
            toast.className = `toast notification-toast notification-${notification.type}`;
            toast.setAttribute('role', 'alert');
            
            toast.innerHTML = `
                <div class="notification-content-wrapper">
                    <div class="notification-accent"></div>
                    <div class="notification-body-main">
                        <button type="button" class="btn-close-custom" aria-label="Close">
                            <i class="fas fa-times"></i>
                        </button>
                        <div class="notification-icon-wrapper">
                            <i class="fas fa-${icon}"></i>
                        </div>
                        <div class="notification-text-wrapper">
                            <div class="fw-bold mb-1">${notification.title}</div>
                            <div class="small text-muted">${notification.message}</div>
                        </div>
                    </div>
                </div>
            `;
            
            const container = document.getElementById('toast-container') || this.createToastContainer();
            container.appendChild(toast);
            
            const closeBtn = toast.querySelector('.btn-close-custom');
            closeBtn.addEventListener('click', () => {
                toast.classList.add('hide');
                setTimeout(() => toast.remove(), 300);
            });

            if (window.bootstrap && bootstrap.Toast) {
                const bsToast = new bootstrap.Toast(toast, { delay: 6000 });
                bsToast.show();
            } else {
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.add('hide');
                    setTimeout(() => toast.remove(), 300);
                }, 6000);
            }
        },

        createToastContainer: function() {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
            return container;
        },

        prependNotificationToList: function(notification) {
            const list = document.querySelector('.notification-list');
            if (!list) return;
            
            const item = this.createNotificationItem(notification);
            list.insertBefore(item, list.firstChild);
            
            const emptyState = list.querySelector('.notification-empty');
            if (emptyState) emptyState.remove();
        },

        createNotificationItem: function(notification) {
            const div = document.createElement('a');
            div.className = 'dropdown-item notification-item d-flex align-items-start py-3 border-bottom';
            if (!notification.is_read) div.classList.add('bg-light');
            
            div.href = notification.link || '#';
            div.dataset.id = notification.id;
            
            const iconMap = {
                'success': 'check-circle text-success',
                'error': 'exclamation-circle text-danger',
                'warning': 'exclamation-triangle text-warning',
                'info': 'info-circle text-info'
            };
            
            const icon = iconMap[notification.type] || 'bell text-secondary';
            
            div.innerHTML = `
                <div class="me-3 mt-1">
                    <div class="icon-circle bg-light d-flex align-items-center justify-content-center">
                        <i class="fas fa-${icon}"></i>
                    </div>
                </div>
                <div class="flex-grow-1">
                    <div class="fw-bold small text-dark">${notification.title}</div>
                    <div class="text-muted smaller text-truncate mb-1">
                        ${notification.message}
                    </div>
                    <div class="text-muted smaller opacity-75">
                        <i class="far fa-clock me-1"></i> ${this.formatTime(notification.created_at)}
                    </div>
                </div>
            `;
            
            div.addEventListener('click', (e) => {
                if (!notification.is_read) {
                    this.markAsRead(notification.id).then(data => {
                        if (data && data.success) {
                            div.classList.remove('bg-light');
                            notification.is_read = true;
                            this.loadUnreadCount();
                        }
                    });
                }
            });
            
            return div;
        },

        formatTime: function(timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = (now - date) / 1000;
            
            if (diff < 60) return this.msgs.justNow;
            
            if (diff < 3600) {
                const mins = Math.floor(diff / 60);
                return this.msgs.minutesAgo.includes('%d') 
                    ? this.msgs.minutesAgo.replace('%d', mins) 
                    : `${mins} ${this.msgs.minutesAgo}`;
            }
            
            if (diff < 86400) {
                const hours = Math.floor(diff / 3600);
                return this.msgs.hoursAgo.includes('%d') 
                    ? this.msgs.hoursAgo.replace('%d', hours) 
                    : `${hours} ${this.msgs.hoursAgo}`;
            }
            
            return date.toLocaleDateString();
        },

        loadUnreadCount: function() {
            if (!this.urls.unreadCount) return;
            fetch(this.urls.unreadCount, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => { if (data.success) this.updateUnreadBadge(data.count); });
        },

        incrementUnreadCount: function() {
            const badge = document.getElementById('notification-badge');
            const currentCount = parseInt(badge?.textContent) || 0;
            this.updateUnreadBadge(currentCount + 1);
        },

        updateUnreadBadge: function(count) {
            const badge = document.getElementById('notification-badge');
            if (badge) {
                badge.textContent = count > 0 ? count : '';
                badge.classList.toggle('d-none', count === 0);
            }
            const headerCount = document.getElementById('notification-count');
            if (headerCount) {
                headerCount.textContent = `${count} ${this.msgs.new}`;
                headerCount.classList.toggle('d-none', count === 0);
            }
        },

        reloadNotifications: function() {
            if (!this.urls.list) return;
            fetch(this.urls.list, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => { if (data.success) this.renderNotificationList(data.notifications); });
        },

        renderNotificationList: function(notifications) {
            const list = document.querySelector('.notification-list');
            if (!list) return;
            list.innerHTML = '';
            if (!notifications || notifications.length === 0) {
                list.innerHTML = `<div class="notification-empty text-center py-5 text-muted">
                    <i class="fas fa-bell-slash fa-3x mb-3 opacity-20"></i>
                    <p class="small mb-0">${this.msgs.empty}</p>
                </div>`;
                return;
            }
            notifications.forEach(n => list.appendChild(this.createNotificationItem(n)));
        },

        markAsRead: function(id) {
            const url = `${this.urls.markReadBase}${id}/read/`;
            return fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).then(res => res.json());
        },

        setupMarkAllRead: function() {
            const btn = document.getElementById('mark-all-read');
            if (btn) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.markAllAsRead();
                });
            }
        },

        markAllAsRead: function() {
            if (!this.urls.markAllRead) return;
            fetch(this.urls.markAllRead, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    this.updateUnreadBadge(0);
                    document.querySelectorAll('.notification-item').forEach(i => i.classList.remove('bg-light'));
                }
            });
        },

        getCsrfToken: function() {
            const name = 'csrftoken';
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    };

    window.NotificationHandler = NotificationHandler;

    // Auto-initialize if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => NotificationHandler.init());
    } else {
        NotificationHandler.init();
    }
})();
