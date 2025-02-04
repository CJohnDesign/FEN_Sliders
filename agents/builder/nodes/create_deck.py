"""Create deck node for initializing deck structure."""
import logging
import shutil
from pathlib import Path
from typing import Dict
from ..state import BuilderState, DeckInfo, WorkflowStage
from ..utils.logging_utils import log_state_change, log_error
from ..utils.state_utils import save_state

# Set up logging
logger = logging.getLogger(__name__)

def read_template_file(file_path: Path) -> str:
    """Read a template file and return its contents.
    
    Args:
        file_path: Path to the template file
        
    Returns:
        str: The file contents or empty string if file doesn't exist
    """
    try:
        if not file_path.exists():
            logger.error(f"Template file not found: {file_path}")
            return ""
            
        with open(file_path) as f:
            return f.read()
            
    except Exception as e:
        logger.error(f"Error reading template file: {str(e)}")
        return ""

async def create_deck_structure(state: BuilderState) -> BuilderState:
    """Create initial deck directory structure."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.CREATE_DECK:
            logger.warning(f"Expected stage {WorkflowStage.CREATE_DECK}, but got {state.current_stage}")
            
        # Get metadata
        if not state.metadata:
            logger.warning("No metadata found in state")
            return state
            
        # Set up paths
        base_dir = Path(__file__).parent.parent.parent.parent
        template_dir = base_dir / "decks" / state.deck_info.template
        deck_dir = base_dir / "decks" / state.metadata.deck_id
        
        # Check template exists
        if not template_dir.exists():
            logger.error(f"Template directory not found: {template_dir}")
            return state
            
        # Check if deck directory already exists and remove it
        if deck_dir.exists():
            logger.info(f"Removing existing deck directory: {deck_dir}")
            try:
                shutil.rmtree(deck_dir)
                logger.info(f"Successfully removed existing deck directory: {deck_dir}")
            except Exception as e:
                logger.error(f"Error removing existing deck directory: {e}")
                return state
        
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
        
        # Read template files
        slides_template = read_template_file(template_dir / "slides.md")
        audio_script_template = read_template_file(template_dir / "audio" / "audio_script.md")
        
        # Update state with template content
        state.slides = slides_template
        state.audio_script = audio_script_template
        
        # Copy template files
        for file in template_dir.glob("*.*"):
            if file.suffix in [".md", ".json", ".yaml", ".yml"]:
                target_file = deck_dir / file.name
                # Replace template content with state content if available
                if file.name == "slides.md" and state.slides:
                    with open(target_file, "w") as f:
                        f.write(state.slides)
                elif file.name == "audio/audio_script.md" and state.audio_script:
                    with open(target_file, "w") as f:
                        f.write(state.audio_script)
                else:
                    shutil.copy2(file, deck_dir)
                logger.info(f"Copied template file: {file.name}")
        
        # Update state with deck info
        deck_info = DeckInfo(
            path=str(deck_dir),
            template=state.deck_info.template
        )
        state.deck_info = deck_info
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="create_deck",
            change_type="complete",
            details={"deck_path": str(deck_dir)}
        )
        
        # Update workflow stage
        state.update_stage(WorkflowStage.CREATE_DECK)
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "create_deck", e)
        state.error_context = {
            "error": str(e),
            "stage": "deck_creation"
        }
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 