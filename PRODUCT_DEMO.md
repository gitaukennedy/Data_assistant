# Enterprise Data Assistant - Product Demo

## Real Application Screenshots (Text-Based)

### 1. WEB INTERFACE - Initial Load

When you run: `python main.py --mode web` and visit `http://localhost:5000`

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│              Enterprise Data Assistant                                  │
│            Natural Language to SQL Query System                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────┬───────────────────────────────┐
│                                          │                               │
│  CHAT MESSAGES AREA                      │   DATABASE SCHEMA SIDEBAR     │
│  ════════════════════════════════════    │   ═════════════════════════   │
│                                          │                               │
│  ┌──────────────────────────────────┐  │   Database Schema             │
│  │ Welcome                          │  │   ─────────────────           │
│  │                                  │  │                               │
│  │ Enterprise Data Assistant.       │  │   [customers]                 │
│  │ Ask questions about your         │  │   • customer_id (INTEGER)     │
│  │ database:                        │  │   • name (VARCHAR)            │
│  │                                  │  │   • email (VARCHAR)           │
│  │ • What is total revenue?         │  │   • region (VARCHAR)          │
│  │ • Which regions have most        │  │   • signup_date (DATE)        │
│  │   customers?                     │  │                               │
│  │ • Show me sales by product       │  │   [orders]                    │
│  └──────────────────────────────────┘  │   • order_id (INTEGER)        │
│                                          │   • customer_id (INTEGER)     │
│                                          │   • product (VARCHAR)         │
│  ┌──────────────────────────────────┐  │   • amount (NUMERIC)          │
│  │ You: What is the total revenue   │  │   • order_date (DATE)         │
│  │ from Enterprise Subscriptions?   │  │                               │
│  └──────────────────────────────────┘  │   [Refresh Schema]            │
│                                          │                               │
│  ┌──────────────────────────────────┐  │                               │
│  │ Assistant: Total Enterprise      │  │                               │
│  │ Subscription revenue: $5,000.00  │  │                               │
│  │                                  │  │                               │
│  │ Query Details:                   │  │                               │
│  │ - Query time: 0.23s              │  │                               │
│  │ - Rows returned: 1               │  │                               │
│  └──────────────────────────────────┘  │                               │
│                                          │                               │
│  [Ask your question here...] [Send] │                               │
│  Status: Ready                      │                               │
│                                          │                               │
└──────────────────────────────────────────┴───────────────────────────────┘

Footer: Powered by Google Gemini 2.5 Flash + PostgreSQL + LangChain
```

---

### 2. USER INTERACTION - Query Response

**User Types:** "Show me the top 3 regions by customer count"

```
SYSTEM FLOW:

1. User Input Processing
   └─ Input: "Show me the top 3 regions by customer count"
   └─ Validation: Passed (valid question)

2. RAG Context Retrieval
   └─ Search Schema: "regions", "customers", "count"
   └─ Retrieved Context: customers table structure + metadata

3. LLM Processing (Gemini 2.5 Flash)
   └─ Input: Question + Schema Context
   └─ Processing Time: 0.18 seconds
   └─ Generated SQL Query:
      SELECT region, COUNT(*) as customer_count
      FROM customers
      GROUP BY region
      ORDER BY customer_count DESC
      LIMIT 3;

4. SQL Validator
   └─ Query Analysis: SELECT query (READ ONLY) ✓
   └─ Security Check: No DROP/DELETE/UPDATE ✓
   └─ Injection Detection: No malicious patterns ✓
   └─ Status: APPROVED

5. Database Execution
   └─ Connected to: PostgreSQL (localhost:5432)
   └─ Execution Time: 0.05 seconds
   └─ Rows Returned: 3

6. Response Formatting
   └─ Query Results:
      
      Region          | Customer Count
      ─────────────────────────────────
      North America   |      2
      Europe          |      2
      Asia-Pacific    |      1
      ─────────────────────────────────

7. Natural Language Response
   └─ "North America and Europe are tied for the most customers 
      with 2 each, followed by Asia-Pacific with 1 customer."

8. Frontend Display
   └─ Message Rendered in Chat
   └─ Auto-Scroll to Latest Message
   └─ Status Updated: "Ready"
   └─ Input Field Cleared & Focused
```

**Chat Display After Query:**

```
Assistant: North America and Europe are tied for the 
most customers with 2 each, followed by Asia-Pacific 
with 1 customer.

Details:
• North America: 2 customers
• Europe: 2 customers  
• Asia-Pacific: 1 customer

Query executed in 0.23 seconds.
```

---

### 3. API ENDPOINT RESPONSE

#### POST /api/ask

**Request:**
```json
{
  "question": "What is the average order amount by product?"
}
```

**Response:**
```json
{
  "status": "success",
  "question": "What is the average order amount by product?",
  "answer": "Here is the average order amount by product type:\n\nEnterprise Subscription: $2,500.00\nPro Plan: $1,200.00\nSupport Package: $500.00\nBasic Plan: $300.00\n\nEnterprise Subscriptions generate the highest average revenue per order.",
  "context_used": true,
  "execution_time": 0.34
}
```

#### GET /api/database/info

**Response:**
```json
{
  "status": "success",
  "tables": [
    "customers",
    "orders"
  ],
  "schemas": {
    "customers": {
      "columns": [
        {"customer_id": "INTEGER"},
        {"name": "VARCHAR"},
        {"email": "VARCHAR"},
        {"region": "VARCHAR"},
        {"signup_date": "DATE"}
      ],
      "primary_key": ["customer_id"]
    },
    "orders": {
      "columns": [
        {"order_id": "INTEGER"},
        {"customer_id": "INTEGER"},
        {"product": "VARCHAR"},
        {"amount": "NUMERIC"},
        {"order_date": "DATE"}
      ],
      "primary_key": ["order_id"]
    }
  }
}
```

#### GET /api/health

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

### 4. CLI MODE EXECUTION

When you run: `python main.py --mode cli`

```
============================================================
Enterprise Text-to-SQL Data Assistant
============================================================
Type your question or 'quit' to exit

You: What is the total revenue generated from Enterprise Subscriptions?