"""LLM utilities for model interactions."""
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

def get_base_config() -> Dict[str, Any]:
    """Get base configuration for LLM models."""
    return {
        "request_timeout": 300,
        "max_retries": 3
    }

async def get_completion(
    messages: List[Dict[str, str]], 
    model: str = "gpt-4o", 
    temperature: float = 0.7,
    model_type: str = "standard"
) -> str:
    """Get a completion from the LLM.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model: Model identifier to use
        temperature: Temperature for generation
        model_type: Type of model usage ("standard" or "reasoning")
        
    Returns:
        Generated completion text
    """
    try:
        # Configure model
        config = get_base_config()
        
        # If model_type is reasoning, use o3-mini, otherwise use gpt-4o
        model = "o3-mini" if model_type == "reasoning" else "gpt-4o"
        
        config.update({
            "model": model,
            "temperature": temperature
        })
        
        llm = ChatOpenAI(**config)
        
        # Convert to LangChain message format
        langchain_messages = [
            SystemMessage(content=msg["content"]) if msg["role"] == "system"
            else HumanMessage(content=msg["content"])
            for msg in messages
        ]
        
        # Make request
        logger.info(f"[GPT Call] Sending request to {model}")
        response = await llm.ainvoke(langchain_messages)
        logger.info("[GPT Call] Received response")
        
        return response.content
        
    except Exception as e:
        logger.error(f"Error in LLM completion: {str(e)}")
        raise

async def get_llm(
    temperature: float = 0.7,
    model: str = "gpt-4o",
    response_format: Optional[Dict[str, str]] = None
) -> ChatOpenAI:
    """Get LLM instance with proper configuration."""
    try:
        # Get base config
        config = get_base_config()
        
        # Add model and temperature
        config.update({
            "model": model,
            "temperature": temperature
        })
        
        # Add response format if specified
        if response_format:
            config["response_format"] = response_format
            
        return ChatOpenAI(**config)
        
    except Exception as e:
        logger.error(f"Error configuring LLM: {str(e)}")
        raise 