import os
import warnings
from dotenv import load_dotenv

# Suppress non-critical deprecation warnings
warnings.filterwarnings("ignore")

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# 1. Connect to PostgreSQL
db_url = os.getenv("DATABASE_URL")
db = SQLDatabase.from_uri(db_url)

# 2. Initialize Supported Gemini LLM Engine
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)

# 3. Create SQL Agent with Tool Calling
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    verbose=True,
    agent_type="tool-calling"
)

def ask_data_assistant(question: str):
    print(f"\n==========================================")
    print(f"User Question: {question}")
    print(f"==========================================\n")
    
    response = agent_executor.invoke({"input": question})
    print(f"\nFinal Answer: {response['output']}\n")

if __name__ == "__main__":
    ask_data_assistant("What is the total revenue generated from Enterprise Subscriptions?")
    ask_data_assistant("Which region has the highest number of customers?")