"""Image processing node for handling presentation images."""
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple
from ..state import BuilderState, PageMetadata, WorkflowStage
from ..utils.logging_utils import log_error, log_state_change
from ..utils.state_utils import save_state
from agents.utils.pdf_utils import convert_pdf_to_images

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Changed to INFO for more visibility

BATCH_SIZE = 5

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

async def process_image_batch(
    batch: List[Path],
    state: BuilderState,
    pages_dir: Path,
    existing_metadata: Dict[int, PageMetadata] = None
) -> List[PageMetadata]:
    """Process a batch of images concurrently."""
    async def process_single_image(image_path: Path, index: int) -> PageMetadata:
        try:
            # Check if metadata already exists for this page
            page_number = index + 1  # 1-based page numbers
            if existing_metadata and page_number in existing_metadata:
                logger.info(f"Using existing metadata for page {page_number}")
                return existing_metadata[page_number]
                
            # Create new page metadata
            page_name = image_path.stem
            content = f"Image content for page {page_number}"
            
            metadata = PageMetadata(
                page_number=page_number,
                page_name=page_name,
                file_path=str(image_path),
                content_type="slide",
                content=content
            )
            
            # Log progress
            log_state_change(
                state=state,
                node_name="process_imgs",
                change_type="image_processed",
                details={
                    "page_number": page_number,
                    "file_path": str(image_path)
                }
            )
            
            logger.info(f"✓ Processed image {page_number}: {image_path.name}")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Error processing image {image_path.name}:")
            logger.error(f"  Error: {str(e)}")
            return None

    # Process batch concurrently
    tasks = [process_single_image(img, idx) for idx, img in enumerate(batch)]
    results = await asyncio.gather(*tasks)
    
    # Filter out failed results
    return [result for result in results if result is not None]

async def process_imgs(state: BuilderState) -> BuilderState:
    """Process images from PDF or existing files while preserving state."""
    try:
        logger.info("Starting process_imgs node")
        
        # Preserve existing state
        existing_metadata = {
            meta.page_number: meta 
            for meta in (preserve_state(state, "page_metadata") or [])
        }
        
        # Verify we're in the correct stage
        expected_stages = [WorkflowStage.CREATE_DECK, WorkflowStage.PROCESS_IMAGES]  # Allow both stages
        if state.current_stage not in expected_stages:
            logger.warning(f"Expected stage {WorkflowStage.PROCESS_IMAGES}, but got {state.current_stage}")
        
        # Check deck info exists
        if not state.deck_info:
            logger.error("❌ No deck info found in state")
            return state
        
        logger.info(f"✓ Found deck info: {state.deck_info.path}")
            
        # Get paths
        deck_dir = Path(state.deck_info.path)
        pdf_dir = deck_dir / "img" / "pdfs"
        pages_dir = deck_dir / "img" / "pages"
        
        logger.info(f"Directories to use:")
        logger.info(f"  - Deck dir: {deck_dir}")
        logger.info(f"  - PDF dir: {pdf_dir}")
        logger.info(f"  - Pages dir: {pages_dir}")
        
        # Create directories if they don't exist
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pages_dir.mkdir(parents=True, exist_ok=True)
        logger.info("✓ Directories created/verified")
        
        # Check for PDFs first
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if pdf_files:
            logger.info(f"✓ Found {len(pdf_files)} PDF files:")
            for pdf in pdf_files:
                logger.info(f"  - {pdf.name}")
                
            # Convert PDFs to images if needed
            logger.info(f"Starting PDF conversion for deck_id: {state.metadata.deck_id}")
            logger.info(f"Converting PDF to images in: {deck_dir}")
            
            # Call convert_pdf_to_images with correct parameters
            result = await convert_pdf_to_images(
                deck_id=state.metadata.deck_id,
                deck_path=str(deck_dir)
            )
            
            if result["status"] == "error":
                error_msg = f"PDF conversion failed: {result.get('error', 'Unknown error')}"
                logger.error(error_msg)
                state.set_error(error_msg, "process_imgs")
                return state
                
            logger.info(f"✓ PDF conversion complete - {result.get('page_count', 0)} pages processed")
            
        # Get all image files
        image_files = sorted(list(pages_dir.glob("*.jpg")) + list(pages_dir.glob("*.png")))
        if not image_files:
            logger.error("❌ No images found to process")
            state.set_error("No images found", "process_imgs")
            return state
            
        logger.info(f"✓ Found {len(image_files)} images to process")
        
        # Process images in batches
        processed_metadata = []
        for i in range(0, len(image_files), BATCH_SIZE):
            batch = image_files[i:i + BATCH_SIZE]
            logger.info(f"Processing batch {i//BATCH_SIZE + 1} of {(len(image_files) + BATCH_SIZE - 1)//BATCH_SIZE}")
            
            batch_metadata = await process_image_batch(
                batch, 
                state, 
                pages_dir,
                existing_metadata
            )
            processed_metadata.extend(batch_metadata)
        
        # Update state with processed metadata
        state.page_metadata = processed_metadata
        
        # Log completion and transition stage
        log_state_change(
            state=state,
            node_name="process_imgs",
            change_type="complete",
            details={
                "processed_images": len(processed_metadata),
                "deck_id": state.metadata.deck_id
            }
        )
        
        # Move to next stage
        transition_stage(state, WorkflowStage.PROCESS_IMAGES, WorkflowStage.PROCESS_SUMMARIES)
        logger.info(f"Saved state for deck {state.metadata.deck_id}")
        logger.info(f"✓ Successfully processed {len(processed_metadata)} images")
        
        return state
        
    except Exception as e:
        error_msg = f"Image processing failed: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "process_imgs")
        return state 