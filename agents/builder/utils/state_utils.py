"""State management utilities for the builder agent."""
import os
import json
import logging
from typing import Optional, Dict, Union
from pathlib import Path
from ..state import BuilderState

# Set up logging
logger = logging.getLogger(__name__)

def load_existing_state(deck_id: str) -> Optional[BuilderState]:
    """Load existing state from state.json if it exists."""
    state_path = Path(f"decks/{deck_id}/state.json")
    if state_path.exists():
        logger.info(f"Loading existing state from {state_path}")
        with open(state_path) as f:
            state_dict = json.load(f)
            return BuilderState.model_validate(state_dict)
    return None

def save_state(state: Union[BuilderState, Dict], deck_id: str) -> None:
    """Save current state to disk."""
    try:
        state_path = Path(f"decks/{deck_id}/state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert state to dictionary format
        if isinstance(state, BuilderState):
            state_dict = state.model_dump(mode='json')
        elif isinstance(state, dict):
            # If it's a dict but contains Pydantic models, convert them
            state_dict = BuilderState.model_validate(state).model_dump(mode='json')
        else:
            raise ValueError(f"Unsupported state type: {type(state)}")
        
        # Write state to file
        with open(state_path, "w") as f:
            json.dump(state_dict, f, indent=2)
            
        logger.info(f"State saved to {state_path}")
        
    except Exception as e:
        logger.error(f"Error saving state: {str(e)}")
        logger.error(f"State type: {type(state)}")
        if isinstance(state, dict):
            logger.error("State keys: " + ", ".join(state.keys())) 