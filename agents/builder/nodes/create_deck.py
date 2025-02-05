"""Create deck node for initializing a new deck."""
import logging
import shutil
from pathlib import Path
from typing import Optional, Any, List, Tuple
from ..state import BuilderState, DeckInfo, DeckMetadata, WorkflowStage
from ..utils.state_utils import save_state
from ..utils.logging_utils import log_state_change, log_error
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

def get_template_files() -> List[Tuple[str, str]]:
    """Get list of template files to copy.
    
    Returns:
        List of (source, destination) tuples
    """
    return [
        ("img/pages/.gitkeep", "img/pages/.gitkeep"),
        ("img/pdfs/.gitkeep", "img/pdfs/.gitkeep"),
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

@traceable(name="copy_template_files")
def copy_template_files(template_dir: Path, deck_dir: Path, state: BuilderState) -> None:
    """Copy template files to deck directory with progress tracking.
    
    Args:
        template_dir: Source template directory
        deck_dir: Target deck directory
        state: Current builder state for progress tracking
    """
    try:
        # Create required directories
        directories = [
            deck_dir / "img" / "pages",
            deck_dir / "img" / "pdfs",
            deck_dir / "img" / "logos",
            deck_dir / "audio"
        ]
        
        # Track directory creation progress
        state.set_stage_progress(
            total=len(directories) + len(get_template_files()),
            completed=0,
            current="Creating directories"
        )
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            state.set_stage_progress(
                total=len(directories) + len(get_template_files()),
                completed=directories.index(directory) + 1,
                current=f"Created directory: {directory.name}"
            )
        
        # Copy template files with progress tracking
        template_files = get_template_files()
        for src, dst in template_files:
            src_path = template_dir / src
            dst_path = deck_dir / dst
            if src_path.exists():
                shutil.copy2(src_path, dst_path)
                state.set_stage_progress(
                    total=len(directories) + len(template_files),
                    completed=len(directories) + template_files.index((src, dst)) + 1,
                    current=f"Copied file: {dst}"
                )
                logger.info(f"Copied template file: {dst}")
            else:
                logger.warning(f"Template file not found: {src}")
                
    except Exception as e:
        logger.error(f"Error copying template files: {str(e)}")
        raise

@traceable(name="create_deck")
async def create_deck(state: BuilderState) -> BuilderState:
    """Create a new deck with initial structure while preserving existing state.
    
    Args:
        state: Current builder state
        
    Returns:
        Updated builder state
    """
    try:
        logger.info("Starting deck creation")
        
        # Verify we're in the correct stage
        if state.workflow_progress.current_stage != WorkflowStage.INIT:
            logger.warning(f"Expected stage {WorkflowStage.INIT}, got {state.workflow_progress.current_stage}")
            state.update_stage(WorkflowStage.INIT)
        
        # Validate required metadata
        if not state.metadata or not state.metadata.deck_id:
            error_msg = "Missing deck ID in metadata"
            logger.error(error_msg)
            state.set_error(error_msg, "create_deck")
            return state
            
        # Set up deck info if not present
        if not state.deck_info:
            deck_dir = Path("decks") / state.metadata.deck_id
            state.deck_info = DeckInfo(
                path=str(deck_dir),
                template="FEN_TEMPLATE"
            )
            
        # Get paths
        deck_dir = Path(state.deck_info.path)
        template_dir = deck_dir.parent / state.deck_info.template
        
        # Track progress
        state.set_stage_progress(
            total=4,  # Major steps: cleanup, directory creation, file copying, finalization
            completed=0,
            current="Starting deck creation"
        )
        
        # Remove existing deck directory if it exists
        if deck_dir.exists():
            logger.info(f"Removing existing deck directory: {deck_dir}")
            shutil.rmtree(deck_dir)
            state.set_stage_progress(total=4, completed=1, current="Cleaned up existing directory")
            
        # Create fresh deck directory and copy template files
        logger.info(f"Creating fresh deck directory: {deck_dir}")
        copy_template_files(template_dir, deck_dir, state)
        state.set_stage_progress(total=4, completed=2, current="Created directory structure")
        
        # Initialize empty state fields
        state.page_metadata = []
        state.page_summaries = []
        state.structured_slides = []
        state.table_data = []
        state.validation_issues = None
        state.validation_state = None
        state.error_context = None
        
        state.set_stage_progress(total=4, completed=3, current="Initialized state fields")
        
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
        
        # Move to next stage (EXTRACT)
        state.update_stage(WorkflowStage.EXTRACT)
        state.set_stage_progress(total=4, completed=4, current="Completed deck creation")
        
        # Save state
        await save_state(state, state.metadata.deck_id)
        return state
        
    except Exception as e:
        error_msg = f"Deck creation failed: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "create_deck")
        return state 