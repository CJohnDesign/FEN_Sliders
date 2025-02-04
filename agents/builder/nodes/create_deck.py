"""Create deck node for initializing a new deck."""
import logging
import shutil
from pathlib import Path
from typing import Optional, Any
from ..state import BuilderState, DeckInfo, DeckMetadata, WorkflowStage
from ..utils.state_utils import save_state
from ..utils.logging_utils import log_state_change, log_error

# Set up logging
logger = logging.getLogger(__name__)

def preserve_state(state: BuilderState, field_name: str) -> Any:
    """Helper to preserve state fields."""
    return getattr(state, field_name, None)

def update_state(state: BuilderState, field_name: str, new_value: Any) -> None:
    """Helper to safely update state fields."""
    if not getattr(state, field_name, None):
        setattr(state, field_name, new_value)
        logger.info(f"Updated state field: {field_name}")

def transition_stage(state: BuilderState, current: WorkflowStage, next_stage: WorkflowStage) -> None:
    """Helper for stage transitions."""
    if state.current_stage == current:
        state.update_stage(next_stage)
        save_state(state, state.metadata.deck_id)
        log_state_change(state, current.value, "complete")
        logger.info(f"Transitioned from {current} to {next_stage}")

def setup_google_drive_config(state: BuilderState) -> None:
    """Set up Google Drive configuration if not already present."""
    try:
        if not state.google_drive_config:
            logger.info("Setting up Google Drive configuration")
            state.google_drive_config = None
            logger.info("Google Drive configuration initialized successfully")
    except Exception as e:
        logger.error(f"Error setting up Google Drive config: {str(e)}")

async def create_deck(state: BuilderState) -> BuilderState:
    """Create a new deck with initial structure while preserving existing state.
    
    Args:
        state: Current builder state
        
    Returns:
        Updated builder state
    """
    try:
        logger.info("Starting deck creation")
        
        # Preserve existing metadata and deck info
        existing_metadata = preserve_state(state, "metadata")
        existing_deck_info = preserve_state(state, "deck_info")
        
        # Validate required state attributes
        if not existing_metadata or not existing_metadata.deck_id:
            logger.error("Missing deck ID in metadata")
            state.set_error("Missing deck ID", "create_deck")
            return state
            
        # Set up deck info if not present
        if not existing_deck_info:
            deck_dir = Path("decks") / existing_metadata.deck_id
            new_deck_info = DeckInfo(
                path=str(deck_dir),
                template="FEN_TEMPLATE"
            )
            update_state(state, "deck_info", new_deck_info)
            
        # Get paths
        deck_dir = Path(state.deck_info.path)
        template_dir = deck_dir.parent / state.deck_info.template
        
        # Remove existing deck directory if it exists
        if deck_dir.exists():
            logger.info(f"Removing existing deck directory: {deck_dir}")
            shutil.rmtree(deck_dir)
            logger.info(f"Successfully removed existing deck directory: {deck_dir}")
            
        # Create fresh deck directory
        logger.info(f"Creating fresh deck directory: {deck_dir}")
        deck_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy template files
        copy_template_files(template_dir, deck_dir)
        
        # Initialize empty state fields if not present
        empty_fields = {
            "page_metadata": [],
            "page_summaries": [],
            "structured_slides": [],
            "table_data": [],
            "aggregated_content": [],
            "validation_issues": None,
            "validation_state": None,
            "error_context": None
        }
        
        for field, default_value in empty_fields.items():
            update_state(state, field, default_value)
        
        # Set up Google Drive config if needed
        setup_google_drive_config(state)
        
        # Log completion and transition stage
        log_state_change(
            state=state,
            node_name="create_deck",
            change_type="complete",
            details={
                "deck_id": state.metadata.deck_id,
                "deck_path": str(deck_dir)
            }
        )
        
        # Move to next stage
        transition_stage(state, WorkflowStage.CREATE_DECK, WorkflowStage.PROCESS_IMAGES)
        
        return state
        
    except Exception as e:
        error_msg = f"Deck creation failed: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "create_deck")
        return state

def copy_template_files(template_dir: Path, deck_dir: Path) -> None:
    """Copy template files to deck directory.
    
    Args:
        template_dir: Source template directory
        deck_dir: Target deck directory
    """
    try:
        # Create required directories
        (deck_dir / "img" / "pages").mkdir(parents=True, exist_ok=True)
        (deck_dir / "img" / "pdfs").mkdir(parents=True, exist_ok=True)
        (deck_dir / "img" / "logos").mkdir(parents=True, exist_ok=True)
        (deck_dir / "audio").mkdir(parents=True, exist_ok=True)
        
        # Copy template files
        template_files = [
            ("img/pages/.gitkeep", "img/pages/.gitkeep"),
            ("img/pdfs/.gitkeep", "img/pdfs/.gitkeep"),
            ("img/pdfs/.DS_Store", "img/pdfs/.DS_Store"),
            ("img/pdfs/Everest_Brochure_REV.pdf", "img/pdfs/Everest_Brochure_REV.pdf"),
            ("img/logos/FirstHealth_logo.png", "img/logos/FirstHealth_logo.png"),
            ("img/logos/USFire-Premier_logo.png", "img/logos/USFire-Premier_logo.png"),
            ("img/logos/.gitkeep", "img/logos/.gitkeep"),
            ("img/logos/Ameritas_logo.png", "img/logos/Ameritas_logo.png"),
            ("img/logos/FEN_logo.svg", "img/logos/FEN_logo.svg"),
            ("img/logos/BWA_logo.png", "img/logos/BWA_logo.png"),
            ("img/logos/MBR_logo.png", "img/logos/MBR_logo.png"),
            ("img/logos/TDK_logo.jpg", "img/logos/TDK_logo.jpg"),
            ("img/logos/EssentialCare_logo.png", "img/logos/EssentialCare_logo.png"),
            ("img/logos/NCE_logo.png", "img/logos/NCE_logo.png"),
            ("img/logos/AFSLIC_logo.png", "img/logos/AFSLIC_logo.png"),
            ("audio_script.md", "audio/audio_script.md"),
            ("slides.md", "slides.md")
        ]
        
        for src, dst in template_files:
            src_path = template_dir / src
            dst_path = deck_dir / dst
            if src_path.exists():
                shutil.copy2(src_path, dst_path)
                logger.info(f"Copied template file: {dst}")
            else:
                logger.warning(f"Template file not found: {src}")
                
    except Exception as e:
        logger.error(f"Error copying template files: {str(e)}")
        raise 