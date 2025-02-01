"""Model configuration for the builder agent."""
from typing import Dict

MODEL_CONFIG = {
    "default": "gpt-4o",  # GPT-4o model with 128k context window
}

MODEL_SETTINGS = {
    "default": {
        "temperature": 0,
        "max_tokens": 16384,  # Maximum output tokens for gpt-4o
    }
}

def get_model_config(task_type: str = "default") -> Dict:
    """Get model configuration with fallback strategy"""
    return {
        "model": MODEL_CONFIG.get(task_type, MODEL_CONFIG["default"]),
        **MODEL_SETTINGS.get(task_type, MODEL_SETTINGS["default"])
    } 