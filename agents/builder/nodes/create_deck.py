"""Create deck node for initializing deck structure."""
import logging
import shutil
from pathlib import Path
from ..state import BuilderState, DeckInfo
from ..utils.logging_utils import log_state_change, log_error
from typing import Dict

# Set up logging
logger = logging.getLogger(__name__)

async def create_deck_structure(state: BuilderState) -> Dict:
    """Create initial deck directory structure."""
    try:
        # Get metadata
        if not state.metadata:
            logger.warning("No metadata found in state")
            return {
                "error_context": {
                    "error": "No metadata available",
                    "stage": "deck_creation"
                }
            }
            
        # Set up paths
        base_dir = Path(__file__).parent.parent.parent.parent
        template_dir = base_dir / "decks" / state.deck_info.template
        deck_dir = base_dir / "decks" / state.metadata.deck_id
        
        # Check template exists
        if not template_dir.exists():
            logger.error(f"Template directory not found: {template_dir}")
            return {
                "error_context": {
                    "error": f"Template {state.deck_info.template} not found",
                    "stage": "deck_creation"
                }
            }
            
        # Check if deck directory already exists and remove it
        if deck_dir.exists():
            logger.info(f"Removing existing deck directory: {deck_dir}")
            try:
                shutil.rmtree(deck_dir)
                logger.info(f"Successfully removed existing deck directory: {deck_dir}")
            except Exception as e:
                logger.error(f"Error removing existing deck directory: {e}")
                return {
                    "error_context": {
                        "error": f"Failed to remove existing deck directory: {str(e)}",
                        "stage": "deck_creation"
                    }
                }
        
        # Create fresh deck directory
        logger.info(f"Creating fresh deck directory: {deck_dir}")
        deck_dir.mkdir(parents=True, exist_ok=True)
        
        # Create and copy directory structure
        for dir_name in ["img/pages", "img/pdfs", "img/logos", "audio", "ai"]:
            # Create directory
            target_dir = deck_dir / dir_name
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy contents if directory exists in template
            template_dir_path = template_dir / dir_name
            if template_dir_path.exists():
                for file in template_dir_path.iterdir():
                    if file.is_file():
                        shutil.copy2(file, target_dir)
                        logger.info(f"Copied template file: {dir_name}/{file.name}")
        
        # Copy template files
        for file in template_dir.glob("*.*"):
            if file.suffix in [".md", ".json", ".yaml", ".yml"]:
                shutil.copy2(file, deck_dir)
                logger.info(f"Copied template file: {file.name}")
        
        # Update state with deck info
        deck_info = DeckInfo(
            path=str(deck_dir),
            template=state.deck_info.template
        )
        
        # Log completion
        log_state_change(
            state=state,
            node_name="create_deck",
            change_type="complete",
            details={"deck_path": str(deck_dir)}
        )
        
        return {
            "deck_info": deck_info.model_dump()
        }
        
    except Exception as e:
        log_error(state, "create_deck", e)
        return {
            "error_context": {
                "error": str(e),
                "stage": "deck_creation"
            }
        } 