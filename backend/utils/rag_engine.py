"""RAG (Retrieval-Augmented Generation) Engine for intelligent query context."""
import os
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

class RAGEngine:
    """Retrieval-Augmented Generation for SQL schema and business context."""
    
    def __init__(self, db_path: str = None):
        """Initialize RAG engine with vector store."""
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", "./chromadb")
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        )
        
        # Initialize vector store
        self.vector_store = Chroma(
            collection_name="sql_schema_context",
            embedding_function=self.embeddings,
            persist_directory=self.db_path
        )
        
    def ingest_schema_documentation(self, schema_docs: dict):
        """Ingest database schema and business documentation.
        
        Args:
            schema_docs: Dictionary with table names as keys and descriptions as values
        """
        documents = []
        for table_name, description in schema_docs.items():
            doc = Document(
                page_content=description,
                metadata={"table": table_name, "type": "schema"}
            )
            documents.append(doc)
        
        self.vector_store.add_documents(documents)
        
    def retrieve_relevant_context(self, query: str, k: int = 3) -> list:
        """Retrieve relevant schema context for a user question.
        
        Args:
            query: User's natural language question
            k: Number of results to retrieve
            
        Returns:
            List of relevant schema documents
        """
        results = self.vector_store.similarity_search(query, k=k)
        return results
    
    def build_context_prompt(self, query: str) -> str:
        """Build contextual prompt with retrieved schema information.
        
        Args:
            query: User's question
            
        Returns:
            Enhanced prompt with relevant context
        """
        relevant_docs = self.retrieve_relevant_context(query)
        context = "\n".join([doc.page_content for doc in relevant_docs])
        
        return f"""Based on the following database schema context:
{context}

Answer this question: {query}

Provide a SQL query that accurately addresses the question."""