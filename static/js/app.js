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
            const answerText = extractAnswerText(data);
            addMessage(answerText, 'assistant');
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

function extractAnswerText(payload) {
    if (payload == null) return 'No answer available';

    if (typeof payload === 'string') return payload;

    if (Array.isArray(payload)) {
        const joined = payload
            .map(item => extractAnswerText(item))
            .filter(Boolean)
            .join('\n\n');
        return joined || 'No answer available';
    }

    if (typeof payload === 'object') {
        if (typeof payload.answer === 'string') return payload.answer;
        if (typeof payload.text === 'string') return payload.text;
        if (typeof payload.output === 'string') return payload.output;
        if (typeof payload.message === 'string') return payload.message;
        if (Array.isArray(payload.content)) return extractAnswerText(payload.content);
        if (Array.isArray(payload.parts)) return extractAnswerText(payload.parts);
        if (typeof payload.answer === 'object') return extractAnswerText(payload.answer);
        if (typeof payload.output === 'object') return extractAnswerText(payload.output);
        return JSON.stringify(payload, null, 2);
    }

    return String(payload);
}

function buildSalesOrderTable(markdownText) {
    const lines = String(markdownText || '')
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(line => line.startsWith('* '));

    if (!lines.length) return null;

    const rows = [];
    for (const line of lines) {
        const match = line.match(/\*\s*\*\*Order ID:\*\*\s*(\d+).*?\*\*Customer ID:\*\*\s*(\d+).*?\*\*Product:\*\*\s*([^,]+).*?\*\*Amount:\*\*\s*\$?([0-9,.]+).*?\*\*Order Date:\*\*\s*([^*]+)$/i);

        if (!match) continue;

        rows.push({
            orderId: match[1],
            customerId: match[2],
            product: match[3].trim(),
            amount: match[4],
            orderDate: match[5].trim()
        });
    }

    if (!rows.length) return null;

    const headers = ['Order ID', 'Customer ID', 'Product', 'Amount', 'Order Date'];
    const body = rows.map(row => `
        <tr>
            <td>${row.orderId}</td>
            <td>${row.customerId}</td>
            <td>${row.product}</td>
            <td>$${Number(row.amount.replace(/,/g, '')).toFixed(2)}</td>
            <td>${row.orderDate}</td>
        </tr>
    `).join('');

    return `
        <div class="sales-table-wrap">
            <table class="sales-table">
                <thead>
                    <tr>${headers.map(header => `<th>${header}</th>`).join('')}</tr>
                </thead>
                <tbody>${body}</tbody>
            </table>
        </div>
    `;
}

// Add message to chat
function addMessage(content, type = 'assistant') {
    const messagesDiv = document.getElementById('messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    msgDiv.id = `msg-${messageCount++}`;

    if (type === 'assistant') {
        const markdownText = String(content || '');
        const tableHtml = buildSalesOrderTable(markdownText);
        msgDiv.innerHTML = tableHtml || marked.parse(markdownText);
    } else {
        const escapedContent = document.createElement('div');
        escapedContent.textContent = String(content || '');
        msgDiv.innerHTML = escapedContent.innerHTML;
    }

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