from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Required API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_ORG_ID = os.getenv('OPENAI_ORG_ID')

# LangSmith Configuration
LANGCHAIN_TRACING_V2 = os.getenv('LANGCHAIN_TRACING_V2', 'true')
LANGCHAIN_PROJECT = os.getenv('LANGCHAIN_PROJECT', 'fen-deck-builder')
LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY')

# Optional settings with defaults
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'claude-3-5-sonnet-20240620')
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))

# Validate required environment variables
required_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        "Please add them to your .env file"
    ) 