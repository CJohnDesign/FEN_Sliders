"""Create deck structure node for the builder agent."""
import os
import logging
import shutil
from pathlib import Path
from typing import Optional
from ..state import BuilderState, WorkflowStage, DeckInfo, GoogleDriveConfig
from ..utils.logging_utils import log_state_change, log_error
from ..utils.state_utils import save_state

# Set up logging
logger = logging.getLogger(__name__)

def read_template_file(file_path: Path) -> Optional[str]:
    """Read template file content."""
    try:
        if file_path.exists():
            with open(file_path) as f:
                return f.read()
        return None
    except Exception as e:
        logger.error(f"Error reading template file {file_path}: {str(e)}")
        return None

async def create_deck_structure(state: BuilderState) -> BuilderState:
    """Create initial deck directory structure."""
    try:
        # Initialize state if starting fresh
        if not hasattr(state, 'current_stage') or state.current_stage == WorkflowStage.INIT:
            logger.info("Initializing fresh state")
            state.current_stage = WorkflowStage.CREATE_DECK
            
        # Initialize deck_info if not present
        if not hasattr(state, 'deck_info') or state.deck_info is None:
            logger.info("Initializing deck_info with FEN_TEMPLATE")
            state.deck_info = DeckInfo(
                path="",  # Will be set after directory creation
                template="FEN_TEMPLATE"  # Use FEN_TEMPLATE instead of default
            )
            
        # Get metadata
        if not state.metadata:
            logger.warning("No metadata found in state")
            return state
            
        # Set up paths
        base_dir = Path(__file__).parent.parent.parent.parent
        template_dir = base_dir / "decks" / state.deck_info.template
        deck_dir = base_dir / "decks" / state.metadata.deck_id
        
        # Initialize Google Drive configuration
        credentials_path = base_dir / "firstenroll-f68aed7de363.json"
        if credentials_path.exists():
            logger.info("Setting up Google Drive configuration")
            state.google_drive_config = GoogleDriveConfig(
                credentials_path=str(credentials_path),
                pdf_folder_name=f"Insurance PDFs - {state.metadata.deck_id}",
                docs_folder_name=f"Generated Docs - {state.metadata.deck_id}"
            )
            logger.info("Google Drive configuration initialized successfully")
        else:
            logger.warning(f"Google Drive credentials not found at {credentials_path}")
            
        # Check template exists
        if not template_dir.exists():
            logger.error(f"Template directory not found: {template_dir}")
            state.set_error(
                f"Template directory not found: {template_dir}",
                "deck_creation",
                {"template": state.deck_info.template}
            )
            return state
            
        # Check if deck directory already exists and remove it
        if deck_dir.exists():
            logger.info(f"Removing existing deck directory: {deck_dir}")
            try:
                shutil.rmtree(deck_dir)
                logger.info(f"Successfully removed existing deck directory: {deck_dir}")
            except Exception as e:
                logger.error(f"Error removing existing deck directory: {e}")
                state.set_error(
                    f"Failed to remove existing deck directory: {str(e)}",
                    "deck_creation"
                )
                return state
                
        # Create fresh deck directory
        logger.info(f"Creating fresh deck directory: {deck_dir}")
        deck_dir.mkdir(parents=True, exist_ok=True)
        
        # Create and copy directory structure
        for dir_name in ["img/pages", "img/pdfs", "img/logos", "audio", "audio/oai", "ai"]:
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
                        
        # Read and copy template files
        # First, copy slides.md
        slides_template_path = template_dir / "slides.md"
        if slides_template_path.exists():
            state.slides = read_template_file(slides_template_path)
            if state.slides:
                slides_target = deck_dir / "slides.md"
                with open(slides_target, "w") as f:
                    f.write(state.slides)
                logger.info("Copied slides.md template")
                
        # Copy audio script and config
        audio_script_path = template_dir / "audio" / "audio_script.md"
        if audio_script_path.exists():
            state.script = read_template_file(audio_script_path)
            if state.script:
                script_target = deck_dir / "audio" / "audio_script.md"
                with open(script_target, "w") as f:
                    f.write(state.script)
                logger.info("Copied audio_script.md template")
                
        audio_config_path = template_dir / "audio" / "audio_config.json"
        if audio_config_path.exists():
            shutil.copy2(audio_config_path, deck_dir / "audio" / "audio_config.json")
            logger.info("Copied audio_config.json template")
            
        # Copy any remaining files from root directory
        for file in template_dir.glob("*.*"):
            if file.suffix in [".json", ".yaml", ".yml"] and file.is_file():
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
            details={
                "deck_path": str(deck_dir),
                "google_drive_configured": state.google_drive_config is not None
            }
        )
        
        return state
            
    except Exception as e:
        log_error(state, "create_deck", e)
        state.error_context = {
            "error": f"Failed to create deck: {str(e)}",
            "stage": "deck_creation"
        }
        return state 