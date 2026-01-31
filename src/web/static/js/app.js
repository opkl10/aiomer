/**
 * Aiomer AI - Main Application JavaScript
 */

// === API Client ===
const API = {
    baseUrl: '/api',

    getToken() {
        return localStorage.getItem('token');
    },

    setToken(token) {
        localStorage.setItem('token', token);
    },

    clearToken() {
        localStorage.removeItem('token');
    },

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'שגיאה בבקשה');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // Auth
    async register(email, username, password, fullName) {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password, full_name: fullName }),
        });
    },

    async login(email, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        this.setToken(data.access_token);
        return data;
    },

    logout() {
        this.clearToken();
        window.location.href = '/login';
    },

    // User
    async getMe() {
        return this.request('/user/me');
    },

    async updateProfile(data) {
        return this.request('/user/me', {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    async changePassword(currentPassword, newPassword) {
        return this.request('/user/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
            }),
        });
    },

    async getUserStats() {
        return this.request('/user/stats');
    },

    async getConversations() {
        return this.request('/user/conversations');
    },

    // Chat
    async sendMessage(message, conversationId = null) {
        return this.request('/chat/send', {
            method: 'POST',
            body: JSON.stringify({
                message,
                conversation_id: conversationId,
            }),
        });
    },

    async getConversation(id) {
        return this.request(`/chat/conversations/${id}`);
    },

    async deleteConversation(id) {
        return this.request(`/chat/conversations/${id}`, {
            method: 'DELETE',
        });
    },

    async trainAI(content, entryType = 'general') {
        return this.request('/chat/train', {
            method: 'POST',
            body: JSON.stringify({ content, entry_type: entryType }),
        });
    },

    async searchKnowledge(query) {
        return this.request(`/chat/search?q=${encodeURIComponent(query)}`);
    },

    // Admin
    async getSystemStats() {
        return this.request('/admin/stats');
    },

    async getUsers() {
        return this.request('/admin/users');
    },

    async updateUser(userId, data) {
        return this.request(`/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    async deleteUser(userId) {
        return this.request(`/admin/users/${userId}`, {
            method: 'DELETE',
        });
    },

    async getTrainingEntries() {
        return this.request('/admin/training-entries');
    },

    async deleteTrainingEntry(id) {
        return this.request(`/admin/training-entries/${id}`, {
            method: 'DELETE',
        });
    },

    async clearKnowledgeBase() {
        return this.request('/admin/knowledge/clear', {
            method: 'POST',
        });
    },
};

// === Auth Check ===
function checkAuth() {
    const token = API.getToken();
    const publicPages = ['/', '/login', '/register'];
    const currentPath = window.location.pathname;

    if (!token && !publicPages.includes(currentPath)) {
        window.location.href = '/login';
        return false;
    }

    return true;
}

// === UI Helpers ===
function showAlert(message, type = 'error') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;

    const container = document.querySelector('.alert-container') || document.body;
    container.prepend(alertDiv);

    setTimeout(() => alertDiv.remove(), 5000);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('he-IL', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// === Chat Functions ===
let currentConversationId = null;

async function loadConversations() {
    try {
        const conversations = await API.getConversations();
        const list = document.getElementById('conversationList');
        if (!list) return;

        list.innerHTML = conversations.map(conv => `
            <div class="conversation-item ${conv.id === currentConversationId ? 'active' : ''}"
                 onclick="loadConversation(${conv.id})"
                 data-id="${conv.id}">
                <h4>${escapeHtml(conv.title)}</h4>
                <span>${formatDate(conv.created_at)}</span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load conversations:', error);
    }
}

async function loadConversation(id) {
    try {
        const conv = await API.getConversation(id);
        currentConversationId = id;

        // Update active state
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.toggle('active', parseInt(item.dataset.id) === id);
        });

        // Update header
        const header = document.querySelector('.chat-header h2');
        if (header) header.textContent = conv.title;

        // Render messages
        const container = document.getElementById('chatMessages');
        if (container) {
            container.innerHTML = conv.messages.map(msg => `
                <div class="message ${msg.role}">
                    ${escapeHtml(msg.content).replace(/\n/g, '<br>')}
                </div>
            `).join('');
            container.scrollTop = container.scrollHeight;
        }
    } catch (error) {
        showAlert('שגיאה בטעינת השיחה');
    }
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    if (!input) return;

    const message = input.value.trim();
    if (!message) return;

    // Add user message to UI
    const container = document.getElementById('chatMessages');
    container.innerHTML += `<div class="message user">${escapeHtml(message)}</div>`;
    container.scrollTop = container.scrollHeight;

    // Clear input
    input.value = '';

    // Show loading
    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'message assistant';
    loadingMsg.innerHTML = '<div class="loading"></div>';
    container.appendChild(loadingMsg);
    container.scrollTop = container.scrollHeight;

    try {
        const response = await API.sendMessage(message, currentConversationId);
        currentConversationId = response.conversation_id;

        // Replace loading with response
        loadingMsg.innerHTML = escapeHtml(response.response).replace(/\n/g, '<br>');

        // Reload conversations list
        loadConversations();
    } catch (error) {
        loadingMsg.remove();
        showAlert('שגיאה בשליחת ההודעה');
    }
}

function newConversation() {
    currentConversationId = null;
    const container = document.getElementById('chatMessages');
    if (container) container.innerHTML = '';

    const header = document.querySelector('.chat-header h2');
    if (header) header.textContent = 'שיחה חדשה';

    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
}

// === Training Functions ===
async function trainAI() {
    const input = document.getElementById('trainInput');
    if (!input) return;

    const content = input.value.trim();
    if (!content) return;

    try {
        const result = await API.trainAI(content);
        if (result.success) {
            showAlert(result.message, 'success');
            input.value = '';
        } else {
            showAlert(result.message);
        }
    } catch (error) {
        showAlert('שגיאה באימון');
    }
}

// === Dashboard Functions ===
async function loadDashboard() {
    try {
        const [user, stats] = await Promise.all([
            API.getMe(),
            API.getUserStats(),
        ]);

        // Update user info
        const nameEl = document.getElementById('userName');
        const emailEl = document.getElementById('userEmail');
        if (nameEl) nameEl.textContent = user.full_name || user.username;
        if (emailEl) emailEl.textContent = user.email;

        // Update stats
        document.getElementById('statConversations').textContent = stats.conversations;
        document.getElementById('statMessages').textContent = stats.messages;
        document.getElementById('statTraining').textContent = stats.training_entries;

    } catch (error) {
        showAlert('שגיאה בטעינת הנתונים');
    }
}

// === Admin Functions ===
async function loadAdminDashboard() {
    try {
        const [stats, users] = await Promise.all([
            API.getSystemStats(),
            API.getUsers(),
        ]);

        // Update stats
        document.getElementById('statTotalUsers').textContent = stats.total_users;
        document.getElementById('statActiveUsers').textContent = stats.active_users;
        document.getElementById('statTotalConversations').textContent = stats.total_conversations;
        document.getElementById('statKnowledgeSize').textContent = stats.knowledge_base_size;

        // Render users table
        const tbody = document.getElementById('usersTableBody');
        if (tbody) {
            tbody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.id}</td>
                    <td>${escapeHtml(user.username)}</td>
                    <td>${escapeHtml(user.email)}</td>
                    <td><span class="badge badge-${user.role === 'admin' ? 'info' : 'success'}">${user.role}</span></td>
                    <td><span class="badge badge-${user.is_active ? 'success' : 'danger'}">${user.is_active ? 'פעיל' : 'מושבת'}</span></td>
                    <td>${formatDate(user.created_at)}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary" onclick="toggleUserStatus(${user.id}, ${!user.is_active})">
                            ${user.is_active ? 'השבת' : 'הפעל'}
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        showAlert('שגיאה בטעינת נתוני הניהול');
    }
}

async function toggleUserStatus(userId, isActive) {
    try {
        await API.updateUser(userId, { is_active: isActive });
        loadAdminDashboard();
        showAlert(isActive ? 'המשתמש הופעל' : 'המשתמש הושבת', 'success');
    } catch (error) {
        showAlert(error.message);
    }
}

async function clearKnowledge() {
    if (!confirm('האם אתה בטוח שברצונך למחוק את כל מאגר הידע?')) return;

    try {
        await API.clearKnowledgeBase();
        showAlert('מאגר הידע נוקה בהצלחה', 'success');
        loadAdminDashboard();
    } catch (error) {
        showAlert('שגיאה בניקוי מאגר הידע');
    }
}

// === Event Listeners ===
document.addEventListener('DOMContentLoaded', () => {
    // Check auth for protected pages
    checkAuth();

    // Chat input enter key
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
});
