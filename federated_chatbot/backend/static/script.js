let currentUser = null;
let currentBot = null;
let token = null;

// DOM Elements
const authButtons = document.getElementById('authButtons');
const userInfo = document.getElementById('userInfo');
const usernameDisplay = document.getElementById('usernameDisplay');
const mainContent = document.getElementById('mainContent');
const adminSection = document.getElementById('adminSection');

// -----------------------------------------------------
// Auth Functions
// -----------------------------------------------------
function showLogin() {
    document.getElementById('loginModal').style.display = 'block';
}

function showRegister() {
    document.getElementById('registerModal').style.display = 'block';
}

function hideModals() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('registerModal').style.display = 'none';
}

async function login(event) {
    event.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        if (response.ok) {
            const data = await response.json();
            token = data.access_token;
            currentUser = username;
            updateUI();
            hideModals();
        } else {
            alert('Login failed!');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Login error!');
    }
}

async function register(event) {
    event.preventDefault();
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        if (response.ok) {
            alert('Registration successful! Please login.');
            hideModals();
            showLogin();
        } else {
            alert('Registration failed!');
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('Registration error!');
    }
}

function logout() {
    currentUser = null;
    token = null;
    currentBot = null;
    updateUI();
    clearChat();
}

function updateUI() {
    if (currentUser) {
        authButtons.style.display = 'none';
        userInfo.style.display = 'block';
        mainContent.style.display = 'block';
        usernameDisplay.textContent = currentUser;

        if (currentUser === 'admin') {
            adminSection.style.display = 'block';
        } else {
            adminSection.style.display = 'none';
        }
    } else {
        authButtons.style.display = 'block';
        userInfo.style.display = 'none';
        mainContent.style.display = 'none';
        adminSection.style.display = 'none';
    }
}

// -----------------------------------------------------
// Bot Selection
// -----------------------------------------------------
function selectBot(bot) {
    currentBot = bot;

    document.querySelectorAll('.bot-card').forEach(card => {
        card.classList.remove('selected');
    });
    document.getElementById(`bot-${bot}`).classList.add('selected');

    document.getElementById('currentBot').textContent = `${getBotDisplayName(bot)} - Ready to chat!`;

    document.getElementById('messageInput').disabled = false;
    document.getElementById('sendButton').disabled = false;

    clearChat();
    addBotMessage(getWelcomeMessage(bot));
    loadChatHistory();
}

function getBotDisplayName(bot) {
    const names = {
        fitness: 'Fitness Coach 💪',
        mental: 'Mental Wellness Mentor 🌱',
        academic: 'Academic Assistant 📚'
    };
    return names[bot] || bot;
}

function getWelcomeMessage(bot) {
    const messages = {
        fitness: "Hello! I'm your Fitness Coach! Ready to crush your health goals? 💪",
        mental: "Welcome! I'm here to support your mental wellness journey. 🌱",
        academic: "Hello! I'm your Academic Assistant, ready to help with your learning goals! 📚"
    };
    return messages[bot] || 'Hello! How can I help you today?';
}

// -----------------------------------------------------
// Chat Functions
// -----------------------------------------------------
function addMessage(message, isUser = false) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    messageDiv.textContent = message;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addBotMessage(message) {
    addMessage(message, false);
}

function addUserMessage(message) {
    addMessage(message, true);
}

function clearChat() {
    document.getElementById('chatMessages').innerHTML = '';
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message || !currentBot) return;

    addUserMessage(message);
    input.value = '';

    try {
        const response = await fetch('/multi_rag_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ bot: currentBot, question: message })
        });

        if (response.ok) {
            const data = await response.json();
            addBotMessage(data.response);
        } else {
            addBotMessage('Sorry, I encountered an error. Please try again.');
        }
    } catch (error) {
        console.error('Chat error:', error);
        addBotMessage('Sorry, I encountered an error. Please try again.');
    }
}

document.getElementById('messageInput').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') sendMessage();
});

// -----------------------------------------------------
// Build Index
// -----------------------------------------------------
async function buildIndex() {
    if (!currentBot) {
        alert('Please select a bot first!');
        return;
    }

    try {
        const response = await fetch('/build_index', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ domain: currentBot })
        });

        if (response.ok) {
            const data = await response.json();
            alert(`Index built successfully! ${data.chunks_indexed} chunks indexed.`);
        } else {
            alert('Failed to build index!');
        }
    } catch (error) {
        console.error('Build index error:', error);
        alert('Error building index!');
    }
}

// -----------------------------------------------------
// Load Chat History
// -----------------------------------------------------
async function loadChatHistory() {
    if (!currentUser || !currentBot) return;

    try {
        const response = await fetch(`/chat/history/${currentBot}?limit=10`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();
            console.log('Chat history:', data);
        }
    } catch (error) {
        console.error('Load history error:', error);
    }
}

// -----------------------------------------------------
// Admin Functions
// -----------------------------------------------------
async function showUserManagement() {
    const adminContent = document.getElementById('adminContent');
    adminContent.innerHTML = '<p>Loading users...</p>';

    try {
        const response = await fetch('/admin/users?username=admin&password=admin123');
        if (response.ok) {
            const users = await response.json();
            let html = '<h4>User Management</h4><div class="user-list">';
            for (const [username, userData] of Object.entries(users)) {
                html += `<div class="user-item">
                    <strong>${username}</strong>
                    <button onclick="viewUserData('${username}')">View Data</button>
                </div>`;
            }
            html += '</div>';
            adminContent.innerHTML = html;
        }
    } catch (error) {
        console.error('Admin error:', error);
    }
}

async function viewUserData(username) {
    try {
        const response = await fetch(`/admin/user_data/${username}?username=admin&password=admin123`);
        if (response.ok) {
            const userData = await response.json();
            alert(`User Data for ${username}:\n${JSON.stringify(userData, null, 2)}`);
        }
    } catch (error) {
        console.error('View user data error:', error);
    }
}

// -----------------------------------------------------
// System Statistics (fixed + auto refresh)
// -----------------------------------------------------
// -----------------------------------------------------
// System Statistics (fixed + verified)
// -----------------------------------------------------
async function showSystemStats() {
    const adminContent = document.getElementById('adminContent');
    adminContent.innerHTML = `
        <h4>System Statistics</h4>
        <p id="totalUsers">Total Users: Loading...</p>
        <p id="activeToday">Active Today: Loading...</p>
        <button onclick="rebuildAllIndexes()">Rebuild All Indexes</button>
    `;

    // Call loadSystemStats once now
    await loadSystemStats();

    // Refresh every 30 seconds
    if (!window.systemStatsInterval) {
        window.systemStatsInterval = setInterval(loadSystemStats, 30000);
    }
}

async function loadSystemStats() {
    console.log("Fetching system stats..."); // Debug log
    try {
        const response = await fetch('/admin/system_stats?username=admin&password=admin123');
        console.log("Stats response status:", response.status); // Debug
        if (response.ok) {
            const data = await response.json();
            console.log("Stats data:", data); // Debug
            const totalElem = document.getElementById('totalUsers');
            const activeElem = document.getElementById('activeToday');
            if (totalElem && activeElem) {
                totalElem.textContent = `Total Users: ${data.total_users}`;
                activeElem.textContent = `Active Today: ${data.active_today}`;
            }
        } else {
            document.getElementById('totalUsers').textContent = 'Total Users: Error';
            document.getElementById('activeToday').textContent = 'Active Today: Error';
        }
    } catch (error) {
        console.error('System stats fetch error:', error);
        document.getElementById('totalUsers').textContent = 'Total Users: Error';
        document.getElementById('activeToday').textContent = 'Active Today: Error';
    }
}


// -----------------------------------------------------
// Rebuild All Indexes
// -----------------------------------------------------
async function rebuildAllIndexes() {
    const adminContent = document.getElementById('adminContent');

    // ✅ Clear previous "Rebuilding..." messages before adding a new one
    const existingMsg = document.getElementById('rebuildStatus');
    if (existingMsg) existingMsg.remove();

    // ✅ Add single rebuilding message
    const rebuildingMsg = document.createElement('p');
    rebuildingMsg.id = 'rebuildStatus';
    rebuildingMsg.textContent = 'Rebuilding all indexes... Please wait.';
    adminContent.appendChild(rebuildingMsg);

    try {
        const response = await fetch(`/admin/rebuild_all_indexes?username=admin&password=admin123`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            console.log('Rebuild results:', data);

            // ✅ Update message to success
            rebuildingMsg.textContent = '✅ All indexes rebuilt successfully!';
            alert('All indexes rebuilt successfully!');
        } else {
            rebuildingMsg.textContent = '❌ Failed to rebuild all indexes.';
            alert('Failed to rebuild all indexes.');
        }
    } catch (error) {
        console.error('Rebuild all indexes error:', error);
        rebuildingMsg.textContent = '❌ Error rebuilding all indexes.';
        alert('Error rebuilding all indexes!');
    }
}


// -----------------------------------------------------
updateUI();
