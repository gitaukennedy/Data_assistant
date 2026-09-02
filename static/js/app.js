// Frontend JavaScript for Data Assistant

const API_BASE = '/api';
let messageCount = 0;

// Initialize app on page load
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('question-form');
    form.addEventListener('submit', sendQuestion);
    
    const refreshBtn = document.getElementById('refresh-schema');
    refreshBtn.addEventListener('click', loadDatabaseSchema);
    
    loadDatabaseSchema();
    addWelcomeMessage();
});

// Add welcome message
function addWelcomeMessage() {
    const messagesDiv = document.getElementById('messages');
    const welcomeMsg = document.createElement('div');
    welcomeMsg.className = 'message assistant';
    welcomeMsg.innerHTML = `
        <strong>Welcome</strong>
        <p>Enterprise Data Assistant. Ask questions about your database:</p>
        <ul style="margin-left: 1.5rem; margin-top: 0.5rem;">
            <li>What is the total revenue?</li>
            <li>Which regions have the most customers?</li>
            <li>Show me sales by product</li>
        </ul>
    `;
    messagesDiv.appendChild(welcomeMsg);
    scrollToBottom();
}

// Send question
async function sendQuestion(event) {
    event.preventDefault();
    
    const input = document.getElementById('question-input');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Add user message
    addMessage(question, 'user');
    input.value = '';
    
    // Show loading state
    const loadingMsg = addMessage('Processing...', 'loading');
    const sendBtn = document.getElementById('send-btn');
    const status = document.getElementById('status');
    
    sendBtn.disabled = true;
    status.textContent = 'Processing...';
    
    try {
        const response = await fetch(`${API_BASE}/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        loadingMsg.remove();
        
        if (!response.ok) {
            const error = await response.json();
            addMessage(`Error: ${error.error || 'Unknown error'}`, 'error');
            status.textContent = 'Error occurred';
            return;
        }
        
        const data = await response.json();
        
        if (data.status === 'error') {
            addMessage(`Error: ${data.error}`, 'error');
        } else {
            addMessage(data.answer, 'assistant');
        }
        
        status.textContent = 'Ready';
    } catch (error) {
        loadingMsg.remove();
        addMessage(`Network error: ${error.message}`, 'error');
        status.textContent = 'Connection error';
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

// Add message to chat
function addMessage(content, type = 'assistant') {
    const messagesDiv = document.getElementById('messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    
    // Escape HTML to prevent XSS
    const escapedContent = document.createElement('div');
    escapedContent.textContent = content;
    
    msgDiv.innerHTML = escapedContent.innerHTML;
    msgDiv.id = `msg-${messageCount++}`;
    messagesDiv.appendChild(msgDiv);
    scrollToBottom();
    
    return msgDiv;
}

// Scroll to bottom
function scrollToBottom() {
    const messagesDiv = document.getElementById('messages');
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Load database schema
async function loadDatabaseSchema() {
    try {
        const response = await fetch(`${API_BASE}/database/info`);
        const data = await response.json();
        
        const schemaList = document.getElementById('schema-list');
        schemaList.innerHTML = '';
        
        if (data.status === 'success' && data.schemas) {
            for (const [tableName, info] of Object.entries(data.schemas)) {
                const tableDiv = document.createElement('div');
                tableDiv.className = 'table-item';
                
                const columns = info.columns.map(col => Object.keys(col)[0]).join(', ');
                tableDiv.innerHTML = `
                    <strong>${tableName}</strong>
                    <small>${columns}</small>
                `;
                
                schemaList.appendChild(tableDiv);
            }
        }
    } catch (error) {
        console.error('Failed to load schema:', error);
        const schemaList = document.getElementById('schema-list');
        schemaList.innerHTML = '<div class="message error">Failed to load schema</div>';
    }
}

// Example questions
const exampleQuestions = [
    "What is the total revenue generated from Enterprise Subscriptions?",
    "Which region has the highest number of customers?",
    "Show me the average order amount by product type",
    "How many orders were placed last month?"
];

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl+Enter to send
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        sendQuestion(new Event('submit'));
    }
});