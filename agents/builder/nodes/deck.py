"""Deck creation and structure management."""
import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict
from ..utils.retry_utils import retry_with_exponential_backoff
from ..utils.logging_utils import setup_logger

# Set up logger
logger = setup_logger(__name__)

@retry_with_exponential_backoff()
def create_deck_structure(state: Dict) -> Dict:
    """Create the initial deck structure and return state."""
    try:
        # Get parameters from state
        metadata = state.get("metadata", {})
        deck_id = metadata.get("deck_id")
        title = metadata.get("title")
        
        if not deck_id or not title:
            raise ValueError("Missing required metadata: deck_id or title")
            
        logger.info(f"Creating deck structure for {deck_id}")
        
        # Create base directory structure
        deck_path = Path("decks") / deck_id
        deck_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (deck_path / "ai").mkdir(exist_ok=True)
        (deck_path / "ai" / "tables").mkdir(exist_ok=True)
        (deck_path / "img").mkdir(exist_ok=True)
        (deck_path / "img" / "pdfs").mkdir(exist_ok=True)
        
        # Create initial metadata
        metadata.update({
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        })
        
        # Save metadata
        with open(deck_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Successfully created deck structure at {deck_path}")
        
        # Update state
        state["deck_info"] = {
            "path": str(deck_path),
            "metadata": metadata
        }
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to create deck structure: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "create_deck_structure"
        }
        return state 