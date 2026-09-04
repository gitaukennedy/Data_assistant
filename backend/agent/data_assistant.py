"""Main Data Assistant Agent with LangChain."""
import os
import logging
import re
from sqlalchemy import text
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.utils.rag_engine import RAGEngine
from backend.utils.sql_validator import SQLValidator
from backend.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

CUSTOM_SYSTEM_PROMPT = """You are an expert enterprise Text-to-SQL assistant querying a relational database.

Database Schema Context:
1. customers (customer_id PRIMARY KEY, name, email, region, signup_date)
2. orders (order_id PRIMARY KEY, customer_id, product, amount, order_date)

Relationships & Join Rules:
- Foreign Key: `orders.customer_id` references `customers.customer_id`.
- For query metrics spanning customer location and order performance, perform explicit joins (`orders JOIN customers ON orders.customer_id = customers.customer_id`).

Security & Operational Rules:
- Only execute read-only SELECT queries. Never run INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, GRANT, or REVOKE statements.
- Always verify column names against schema context before rendering SQL queries.
- Formulate clear, concise, and professional natural language summaries for numerical outputs.
"""

class DataAssistant:
    """Enterprise Text-to-SQL Data Assistant using Google Gemini."""
    
    def __init__(self):
        """Initialize the Data Assistant with LLM, database, and RAG."""
        try:
            # Initialize database connection via DB Manager
            self.db_manager = DatabaseManager()
            self.db = self.db_manager.db
            
            # Initialize Google Gemini LLM
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0,
                top_p=0.95
            )
            self.rag_engine = None
            self.agent_executor = None
            logger.info("DataAssistant initialized with Database and Gemini model")
        except Exception as e:
            logger.error(f"Failed to initialize DataAssistant: {e}")
            raise

    def _populate_rag_with_schema(self):
        """Populate RAG engine with database schema documentation."""
        try:
            schemas = self.db_manager.get_table_schemas()
            schema_docs = {
                table: f"Table: {table}\nColumns: {', '.join([list(col.keys())[0] for col in info['columns']])}"
                for table, info in schemas.items()
            }
            self.rag_engine.ingest_schema_documentation(schema_docs)
            logger.info("RAG engine populated with schema documentation")
        except Exception as e:
            logger.warning(f"Failed to populate RAG: {e}")

    def _initialize_ai_components(self):
        """Lazy load the embedding model and SQL agent only when fast-path bypass fails."""
        if self.agent_executor is not None:
            return

        try:
            self.rag_engine = RAGEngine()
            self._populate_rag_with_schema()
            
            self.agent_executor = create_sql_agent(
                llm=self.llm,
                db=self.db,
                verbose=True,
                agent_type="tool-calling",
                max_iterations=5,
                prefix=CUSTOM_SYSTEM_PROMPT,
                handle_parsing_errors=True
            )
            logger.info("LangChain SQL Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to load AI agent components: {e}")
            raise

    def answer_question(self, question: str) -> dict:
        """Process a user question and return formatted answer payload.
        
        Args:
            question: User's natural language question
            
        Returns:
            Dictionary containing response payload and operational metadata
        """
        if not question or not question.strip():
            return {
                "status": "error",
                "question": question,
                "answer": "Please provide a valid question.",
                "context_used": False,
            }

        try:
            # Check fast-path cache / exact pattern matching first
            fast_result = self._fast_path_answer(question)
            if fast_result is not None:
                return fast_result

            # Initialize LangChain Agent & RAG lazily
            self._initialize_ai_components()
            
            # Retrieve Schema Context from Vector Store
            context = self.rag_engine.build_context_prompt(question)
            
            # Formulate structured prompt input
            input_prompt = f"""Relevant schema and relationship context:
{context}

User Question: {question}"""

            # Execute LangChain SQL Agent Execution Cycle
            response = self.agent_executor.invoke({"input": input_prompt})
            answer = response.get("output", "No concise answer could be generated.")
            
            logger.info(f"Question processed successfully via Agent: {question[:50]}...")
            return {
                "status": "success",
                "question": question,
                "answer": answer,
                "context_used": len(context) > 0,
                "fast_path": False
            }

        except Exception as e:
            logger.exception(f"Error processing query agent workflow: {e}")
            
            # Contextual fallback response if Agent fails
            return {
                "status": "success",
                "question": question,
                "answer": (
                    "I encountered an issue executing that dynamic lookup. "
                    "You can try rephrasing or asking standard queries such as "
                    "'total revenue', 'sales by product', 'customers by region', or 'order count'."
                ),
                "context_used": False,
                "fallback": True,
            }

    def _fast_path_answer(self, question: str):
        """Interprets common intents and minimalist keyword queries without an LLM round trip."""
        normalized = re.sub(r"[^a-z0-9 ]", " ", question.lower())
        normalized = " ".join(normalized.split())

        # Greeting & standard meta responses
        if normalized in {"hello", "hi", "hey", "good morning", "good afternoon"}:
            return self._instant_response(question, "Hello. Ask me about your sales, revenue, or customer distributions.")

        if normalized in {"thanks", "thank you", "thx"}:
            return self._instant_response(question, "You are welcome! Let me know if you need more data analysis.")

        if normalized in {"help", "what can you do"}:
            return self._instant_response(
                question,
                "I can analyze database records for metrics on sales volume, product revenue, regional customer density, and average order metrics.",
            )

        # Keyword mapping to SQL queries
        if "total revenue" in normalized or "total sales" in normalized or normalized in {"revenue", "total revenue"}:
            query = text("SELECT COALESCE(SUM(amount), 0) AS total_revenue FROM orders")
            answer_template = "Total revenue is ${:,.2f}."

        elif (
            "sales by product" in normalized
            or "revenue by product" in normalized
            or normalized in {"sales", "sales report"}
        ):
            query = text(
                "SELECT product, SUM(amount) AS revenue "
                "FROM orders GROUP BY product ORDER BY revenue DESC"
            )
            answer_template = None

        elif ("region" in normalized and "customer" in normalized) or normalized in {"customers", "regions"}:
            query = text(
                "SELECT region, COUNT(*) AS customer_count "
                "FROM customers GROUP BY region ORDER BY customer_count DESC"
            )
            answer_template = None

        elif "average" in normalized and "order" in normalized and "amount" in normalized:
            query = text(
                "SELECT product, AVG(amount) AS average_amount "
                "FROM orders GROUP BY product ORDER BY average_amount DESC"
            )
            answer_template = None

        elif "how many" in normalized and "order" in normalized:
            query = text("SELECT COUNT(*) AS order_count FROM orders")
            answer_template = "There are {} orders in total."

        else:
            return None

        # Execute direct SQL via Engine Connection
        with self.db_manager.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()

        if answer_template:
            val_key = "total_revenue" if "total_revenue" in rows[0] else "order_count"
            value = rows[0].get(val_key)
            answer = answer_template.format(value if "{}" in answer_template else float(value))
            
        elif rows and "average_amount" in rows[0]:
            answer = "\n".join(
                f"• {row['product']}: ${float(row['average_amount']):,.2f} average"
                for row in rows
            )
        elif rows and "customer_count" in rows[0]:
            answer = "\n".join(
                f"• {row['region']}: {row['customer_count']} customers" for row in rows
            )
        else:
            answer = "\n".join(
                f"• {row['product']}: ${float(row['revenue']):,.2f}" for row in rows
            )

        return {
            "status": "success",
            "question": question,
            "answer": answer,
            "context_used": False,
            "fast_path": True,
        }

    @staticmethod
    def _instant_response(question: str, answer: str) -> dict:
        """Utility wrapper for direct static string responses."""
        return {
            "status": "success",
            "question": question,
            "answer": answer,
            "context_used": False,
            "fast_path": True,
        }

    def get_database_info(self) -> dict:
        """Retrieve database schema structural metadata for frontend preview components."""
        try:
            schemas = self.db_manager.get_table_schemas()
            return {
                "status": "success",
                "tables": list(schemas.keys()),
                "schemas": schemas
            }
        except Exception as e:
            logger.error(f"Failed to retrieve database schema info: {e}")
            return {"status": "error", "error": str(e)}