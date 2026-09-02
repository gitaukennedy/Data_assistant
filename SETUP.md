# Data Assistant - Complete Setup Guide

## Prerequisites

- Python 3.10+
- PostgreSQL 16 (running locally or remotely)
- Google Gemini API Key
- Node.js (optional, for frontend enhancements)

## Step 1: Environment Setup

### 1.1 Clone and Install

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Configure Environment Variables

```bash
# Copy example .env file
cp .env.example .env

# Edit .env with your credentials
# GEMINI_API_KEY=your_key_here
# DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/company_db
```

## Step 2: Database Setup

### 2.1 Create Database

```bash
python create_db.py
```

### 2.2 Seed Database with Sample Data

```bash
python seed_db.py
```

## Step 3: Running the Application

### Option A: Web Mode (Recommended)

```bash
python main.py --mode web
```

Access at: `http://localhost:5000`

### Option B: CLI Mode

```bash
python main.py --mode cli
```

## Step 4: Test the System

### Via Web UI:
1. Navigate to http://localhost:5000
2. Try example questions:
   - "What is the total revenue generated from Enterprise Subscriptions?"
   - "Which region has the highest number of customers?"
   - "Show me the average order amount by product"

### Via API:

```bash
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the total revenue?"}'
```

### Via CLI:

```bash
python main.py --mode cli
> What is the total revenue?
```

## Architecture

```
┌─────────────────────────────────────┐
│      Frontend (HTML/CSS/JS)         │
│   - Chat interface                  │
│   - Schema explorer                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Flask API Backend                │
│   - /api/ask                        │
│   - /api/database/info              │
│   - /api/health                     │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
  RAG Engine    Data Assistant Agent
  - Schema         - LLM (Gemini)
  - Context        - SQL Tools
  - Embeddings     - Query Validator
       │               │
       └───────┬───────┘
               │
               ▼
      PostgreSQL Database
      - customers table
      - orders table
```

## Project Structure

```
Data_assisstant/
├── app.py                          # Flask application
├── main.py                         # Entry point
├── requirements.txt                # Dependencies
├── .env.example                    # Environment template
├── SETUP.md                        # This file
│
├── backend/
│   ├── agent/
│   │   └── data_assistant.py      # Main AI agent
│   ├── database/
│   │   └── db_manager.py          # Database operations
│   ├── routes/
│   │   └── api.py                 # API endpoints
│   └── utils/
│       ├── rag_engine.py          # RAG implementation
│       ├── sql_validator.py       # Query validation
│       └── logger.py              # Logging setup
│
├── templates/
│   └── index.html                 # Frontend HTML
│
├── static/
│   ├── css/
│   │   └── style.css              # Styling
│   └── js/
│       └── app.js                 # Frontend logic
│
├── create_db.py                    # Database creation
└── seed_db.py                      # Sample data
```

## Key Features

✅ **Natural Language to SQL**: Ask questions in English, get results instantly
✅ **RAG Enhancement**: Context-aware responses using vector embeddings
✅ **Security First**: Query validation prevents destructive operations
✅ **Beautiful UI**: Modern chat interface with schema explorer
✅ **Production Ready**: Logging, error handling, rate limiting
✅ **Multi-Mode**: CLI for testing, Web for production

## Troubleshooting

### "Connection refused" error
- Verify PostgreSQL is running: `psql -U postgres`
- Check DATABASE_URL in .env
- Run `python create_db.py` and `python seed_db.py`

### "GEMINI_API_KEY" error
- Get key from: https://makersuite.google.com/app/apikey
- Add to .env file

### Slow responses
- Check network connection
- Verify Gemini API quota
- Review logs in app.log

## Performance Tips

1. **Indexing**: Add indexes on frequently queried columns
2. **Connection Pooling**: Configured in SQLAlchemy
3. **Caching**: RAG embeddings are persisted locally
4. **Batch Operations**: Use for large data imports

## Security Considerations

1. **SQL Injection Prevention**: Query validator blocks dangerous patterns
2. **Read-Only Queries**: Only SELECT statements allowed
3. **Secrets Management**: Use .env for sensitive data
4. **CORS Configuration**: Restricted to trusted origins
5. **Rate Limiting**: Built-in protection against abuse

## Next Steps

1. Extend schema with your production tables
2. Customize RAG documentation
3. Add authentication for multi-user scenarios
4. Deploy using Docker/Kubernetes
5. Monitor with application logging

## Support

For issues or questions, check:
- Application logs: `app.log`
- API response status codes
- Database connectivity: `python -c "from backend.database.db_manager import DatabaseManager; DatabaseManager().health_check()"`
