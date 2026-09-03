"""Main Data Assistant Agent with LangChain."""
import os
import logging
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.utils.rag_engine import RAGEngine
from backend.utils.sql_validator import SQLValidator
from backend.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class DataAssistant:
    """Enterprise Text-to-SQL Data Assistant using Google Gemini."""
    
    def __init__(self):
        """Initialize the Data Assistant with LLM, database, and RAG."""
        try:
            # Initialize database
            self.db_manager = DatabaseManager()
            self.db = self.db_manager.db
            
            # Initialize LLM
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0,
                top_p=0.95
            )
            
            # Initialize RAG Engine
            self.rag_engine = RAGEngine()
            self._populate_rag_with_schema()
            
            # Create SQL Agent
            self.agent_executor = create_sql_agent(
                llm=self.llm,
                db=self.db,
                verbose=True,
                agent_type="tool-calling",
                max_iterations=5
            )
            
            logger.info("DataAssistant initialized successfully")
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
    
    def answer_question(self, question: str) -> dict:
        """Process a user question and return answer.
        
        Args:
            question: User's natural language question
            
        Returns:
            Dictionary with answer, query, and metadata
        """
        try:
            # Get RAG context
            context = self.rag_engine.build_context_prompt(question)
            
            # Execute agent
            response = self.agent_executor.invoke({
                "input": f"""You are answering a business analytics question.
Only use read-only SELECT queries. Never run INSERT, UPDATE, DELETE, DROP, ALTER,
CREATE, GRANT, REVOKE, or any other write/admin statement.

Relevant schema context:
{context}

User question: {question}"""
            })
            
            answer = response.get('output', 'No answer generated')
            
            logger.info(f"Question answered: {question[:50]}...")
            return {
                'status': 'success',
                'question': question,
                'answer': answer,
                'context_used': len(context) > 0
            }
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return {
                'status': 'error',
                'question': question,
                'error': str(e)
            }
    
    def get_database_info(self) -> dict:
        """Get database schema information for frontend.
        
        Returns:
            Database metadata
        """
        try:
            schemas = self.db_manager.get_table_schemas()
            return {
                'status': 'success',
                'tables': list(schemas.keys()),
                'schemas': schemas
            }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {'status': 'error', 'error': str(e)}
