"""Model configuration for the builder agent."""
from typing import Dict

MODEL_CONFIG = {
    "default": "gpt-4o",  # GPT-4o model
    "reasoning": "o3-mini-2025-01-31"  # o3-mini model for reasoning tasks
}

MODEL_SETTINGS = {
    "default": {
        "model": "gpt-4o", # Always use gpt-4o for default and vision tasks, as it has vision capabilities
        "temperature": 0.125,
        "max_tokens": 16384,  # Maximum output tokens for gpt-4o
        "request_timeout": 600,
        "max_retries": 3
    },
    "reasoning": {
        "model": "o3-mini-2025-01-31",
        "temperature": 0.7,
        "max_tokens": 100000,  # o3-mini supports 100k output tokens
        "context_length": 200000  # o3-mini supports 200k context window
    }
}

def get_model_config(task_type: str = "default") -> Dict:
    """Get model configuration with fallback strategy.
    
    Args:
        task_type: Type of task ("default" or "reasoning")
        
    Returns:
        Dict with model configuration including model name and settings
    """
    return MODEL_SETTINGS.get(task_type, MODEL_SETTINGS["default"]) 