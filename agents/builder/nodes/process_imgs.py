"""Image processing node for handling presentation images."""
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple
from ..state import BuilderState, PageMetadata
from ..utils.logging_utils import log_error, log_state_change
from agents.utils.pdf_utils import convert_pdf_to_images

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Changed to INFO for more visibility

BATCH_SIZE = 5

async def process_image_batch(
    batch: List[Path],
    state: BuilderState,
    pages_dir: Path
) -> List[PageMetadata]:
    """Process a batch of images concurrently."""
    async def process_single_image(image_path: Path, index: int) -> PageMetadata:
        try:
            # Create page metadata
            page_number = index + 1  # 1-based page numbers
            page_name = image_path.stem
            
            metadata = PageMetadata(
                page_number=page_number,
                page_name=page_name,
                file_path=str(image_path),
                content_type="slide"
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
    """Process images from PDF or existing files."""
    try:
        logger.info("Starting process_imgs node")
        
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
        if not pdf_files:
            logger.error("❌ No PDF files found in img/pdfs directory")
            logger.error(f"  Searched in: {pdf_dir}")
            logger.error("  Please ensure a PDF file is placed in this directory")
            return state
            
        logger.info(f"✓ Found {len(pdf_files)} PDF files:")
        for pdf in pdf_files:
            logger.info(f"  - {pdf.name}")
            
        # Convert PDF to images
        logger.info(f"Starting PDF conversion for deck_id: {state.metadata.deck_id}")
        logger.info(f"Converting PDF to images in: {deck_dir}")
        
        result = await convert_pdf_to_images(state.metadata.deck_id, str(deck_dir))
        if result["status"] == "error":
            logger.error(f"❌ PDF conversion failed:")
            logger.error(f"  Error: {result['error']}")
            logger.error(f"  Deck ID: {state.metadata.deck_id}")
            logger.error(f"  Directory: {deck_dir}")
            return state
        
        # Verify images were created
        created_images = list(pages_dir.glob("*.jpg")) or list(pages_dir.glob("*.png"))
        logger.info(f"✓ PDF conversion complete")
        
        if not created_images:
            logger.error("❌ No images found after PDF conversion")
            return state
            
        logger.info(f"✓ Found {len(created_images)} images to process")
        
        # Process images in batches
        all_metadata = []
        for i in range(0, len(created_images), BATCH_SIZE):
            batch = created_images[i:i + BATCH_SIZE]
            logger.info(f"Processing batch {i//BATCH_SIZE + 1} of {(len(created_images) + BATCH_SIZE - 1)//BATCH_SIZE}")
            
            batch_results = await process_image_batch(batch, state, pages_dir)
            all_metadata.extend(batch_results)
            
        # Sort metadata by page number
        all_metadata.sort(key=lambda x: x.page_number)
        
        # Update state with all metadata
        state.page_metadata = all_metadata
        state.slide_count = len(all_metadata)
        
        # Log completion
        log_state_change(
            state=state,
            node_name="process_imgs",
            change_type="complete",
            details={
                "total_images": len(all_metadata),
                "deck_path": str(deck_dir)
            }
        )
        
        logger.info(f"✓ Successfully processed {len(all_metadata)} images")
        return state
        
    except Exception as e:
        logger.error("❌ Error in process_imgs:")
        logger.error(f"  Type: {type(e).__name__}")
        logger.error(f"  Error: {str(e)}")
        if state.deck_info:
            logger.error(f"  Deck path: {state.deck_info.path}")
        return state 