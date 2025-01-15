"""LangSmith configuration and setup."""
import os
from dotenv import load_dotenv
from langsmith import Client

# Load environment variables
load_dotenv()

def init_langsmith():
    """Initialize LangSmith configuration."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        raise ValueError("LANGSMITH_API_KEY environment variable is not set")
    
    # Set environment variables for LangChain
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "fen-deck-builder"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    
    return Client()

# Initialize the client
client = init_langsmith() 