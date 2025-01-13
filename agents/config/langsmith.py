"""LangSmith configuration and setup."""
import os
from dotenv import load_dotenv
from langchain.callbacks.manager import tracing_v2_enabled
from langsmith import Client

# Load environment variables
load_dotenv()

def init_langsmith():
    """Initialize LangSmith configuration."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        raise ValueError("LANGSMITH_API_KEY environment variable is not set")
    
    # Set environment variables for LangChain
    os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "true")
    os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "fen-deck-builder")
    os.environ["LANGCHAIN_API_KEY"] = api_key
    
    # Initialize client with loaded environment variables
    return Client()

def get_tracing_context(project_name: str = None):
    """Get a context manager for tracing."""
    return tracing_v2_enabled(
        project_name=project_name or os.getenv("LANGSMITH_PROJECT", "fen-deck-builder")
    )

# Initialize the client
client = init_langsmith() 