import os
import logging
from typing import Dict, Any
from pathlib import Path
from ...utils import audio_utils
from ..state import BuilderState

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('builder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def setup_audio(state: BuilderState) -> BuilderState:
    """Sets up audio configuration and generates script"""
    try:
        # Skip if there was an error in previous steps
        if state.get("error_context"):
            return state
            
        # Check for processed summaries
        if not state.get("processed_summaries"):
            state["error_context"] = {
                "error": "No processed summaries available",
                "stage": "audio_setup"
            }
            return state
            
        # Set up audio script and config
        success = await audio_utils.setup_audio(
            state["metadata"].deck_id,
            state["metadata"].template,
            [],  # Empty slides list since we're using processed summaries
            state["processed_summaries"]
        )
        
        if not success:
            state["error_context"] = {
                "error": "Failed to set up audio",
                "stage": "audio_setup"
            }
            return state
            
        state["audio_config"] = {
            "config_path": f"decks/{state['metadata'].deck_id}/audio/audio_config.json",
            "script_path": f"decks/{state['metadata'].deck_id}/audio/audio_script.md",
            "slide_count": len(state.get("slides", []))
        }
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "audio_setup"
        }
        return state 

async def process_audio(state: BuilderState) -> BuilderState:
    """Process audio files for the deck."""
    try:
        logger.info("Starting audio processing...")
        logger.info(f"State contains: {list(state.keys())}")
        
        # Get deck directory
        deck_dir = state.get("deck_info", {}).get("path")
        if not deck_dir:
            logger.error("No deck directory found in state")
            state["error_context"] = {
                "error": "No deck directory found in state",
                "stage": "audio_processing"
            }
            return state
            
        logger.info(f"Working with deck directory: {deck_dir}")
        
        # Create audio directory
        audio_dir = os.path.join(deck_dir, "ai", "audio")
        os.makedirs(audio_dir, exist_ok=True)
        logger.info(f"Created/verified audio directory at: {audio_dir}")
        
        # TODO: Implement audio processing logic
        logger.info("Audio processing placeholder - functionality to be implemented")
        
        return state
        
    except Exception as e:
        logger.error("Critical error in process_audio")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        state["error_context"] = {
            "error": str(e),
            "stage": "audio_processing"
        }
        return state 