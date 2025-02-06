"""Image processing node for handling presentation images."""
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
from ..state import BuilderState, PageMetadata, WorkflowStage, DeckInfo, PageSummary
from ..utils.logging_utils import log_error, log_state_change
from ..utils.state_utils import save_state
from agents.utils.pdf_utils import convert_pdf_to_images
from langsmith.run_helpers import traceable
from langchain.prompts import ChatPromptTemplate
from agents.utils.llm_utils import get_llm
import base64

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BATCH_SIZE = 5

@traceable(name="collect_image_metadata")
async def collect_image_metadata(image_path: Path, page_number: int) -> PageMetadata:
    """Collect basic metadata about an image and generate a descriptive title."""
    try:
        # Get basic image info
        with Image.open(image_path) as img:
            width, height = img.size
            format = img.format
            mode = img.mode
        
        # Encode image for model
        image_data = encode_image_to_base64(str(image_path))
        
        # Generate descriptive title using OpenAI with image
        llm = await get_llm(temperature=0.7)
        messages = [
            {"role": "system", "content": "You are an expert at creating descriptive titles for insurance presentation slides. Create a 15-20 word title that describes the content and purpose of this slide. The title should be clear and professional."},
            {"role": "user", "content": [
                {"type": "text", "text": f"Create a descriptive title for slide {page_number} that will be used as a filename. The title should be separated by underscores and be safe for use in a filename (no special characters)."},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]}
        ]
        
        title_response = await llm.ainvoke(messages)
        descriptive_title = title_response.content.strip().replace(" ", "_").replace("-", "_")
        descriptive_title = "".join(c for c in descriptive_title if c.isalnum() or c == "_")
        
        # Clear the image data from memory explicitly
        del image_data
        
        # Create new filename with order prefix
        new_filename = f"{page_number:02d}_from_{descriptive_title}.jpg"
        new_path = image_path.parent / new_filename
        
        # Rename the file
        try:
            image_path.rename(new_path)
            logger.info(f"Renamed image to: {new_filename}")
        except Exception as e:
            logger.error(f"Failed to rename image {image_path.name}: {str(e)}")
            new_path = image_path  # Fallback to original path if rename fails
        
        # Create basic content string
        content = (
            f"Image Information:\n"
            f"Title: {descriptive_title.replace('_', ' ')}\n"
            f"Dimensions: {width}x{height}\n"
            f"Format: {format}\n"
            f"Mode: {mode}\n"
            f"File: {new_path.name}"
        )
        
        # Create metadata
        metadata = PageMetadata(
            page_number=page_number,
            page_name=f"page_{page_number:02d}",
            file_path=str(new_path),
            content_type="slide",
            content=content,
            descriptive_title=descriptive_title.replace('_', ' ')
        )
        
        logger.info(f"✓ Collected metadata for page {page_number}")
        return metadata
        
    except Exception as e:
        logger.error(f"Error collecting metadata for {image_path.name}: {str(e)}")
        return None

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64.
    WARNING: The returned base64 string should never be logged or stored in state.
    It should only be used for immediate processing and then discarded.
    """
    with open(image_path, "rb") as image_file:
        # Get file extension to determine mime type
        ext = Path(image_path).suffix.lower()
        mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
        # Create proper data URL format
        return f"data:{mime_type};base64,{base64.b64encode(image_file.read()).decode('utf-8')}"

@traceable(name="process_image_batch")
async def process_image_batch(
    batch: List[Path],
    state: BuilderState,
    start_index: int
) -> List[PageMetadata]:
    """Process a batch of images to collect metadata."""
    results = []
    for i, img_path in enumerate(batch):
        try:
            page_number = start_index + i + 1  # 1-based page numbers
            metadata = await collect_image_metadata(img_path, page_number)
            if metadata:
                results.append(metadata)
                
            # Update progress
            state.set_stage_progress(
                total=len(batch),
                completed=i + 1,
                current=f"Processing page {page_number}"
            )
        except Exception as e:
            logger.error(f"Failed to process {img_path}: {str(e)}")
            continue
            
    return results

@traceable(name="process_imgs")
async def process_imgs(state: BuilderState) -> BuilderState:
    """Process images from PDF and prepare for summary generation."""
    try:
        logger.info("Starting process_imgs node")
        
        # Verify we're in the correct stage
        if state.workflow_progress.current_stage != WorkflowStage.EXTRACT:
            logger.warning(f"Expected stage {WorkflowStage.EXTRACT}, got {state.workflow_progress.current_stage}")
            state.update_stage(WorkflowStage.EXTRACT)
        
        # Initialize deck info if missing
        if not state.deck_info and state.metadata and state.metadata.deck_id:
            state.deck_info = DeckInfo(
                path=f"decks/{state.metadata.deck_id}",
                template="FEN_TEMPLATE"
            )
            logger.info(f"Initialized deck info for {state.metadata.deck_id}")
        
        # Check deck info exists
        if not state.deck_info:
            error_msg = "No deck info found in state and unable to initialize"
            logger.error(f"❌ {error_msg}")
            state.set_error(error_msg, "process_imgs")
            return state
        
        logger.info(f"✓ Found deck info: {state.deck_info.path}")
            
        # Get paths
        deck_dir = Path(state.deck_info.path)
        pdf_dir = deck_dir / "img" / "pdfs"
        pages_dir = deck_dir / "img" / "pages"
        
        # Set initial progress
        state.set_stage_progress(
            total=3,  # PDF conversion, image verification, metadata collection
            completed=0,
            current="Starting image processing"
        )
        
        # Create directories if they don't exist
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pages_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert PDFs to images
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if pdf_files:
            logger.info(f"Converting PDF to images in: {deck_dir}")
            result = await convert_pdf_to_images(
                deck_id=state.metadata.deck_id,
                deck_path=str(deck_dir)
            )
            
            if result["status"] == "error":
                error_msg = f"PDF conversion failed: {result['error']}"
                logger.error(f"❌ {error_msg}")
                state.set_error(error_msg, "process_imgs")
                return state
                
            logger.info(f"✓ PDF conversion completed - {result['page_count']} pages")
            await asyncio.sleep(2)  # Small delay to ensure files are written
            
        # Verify images exist and are readable
        image_files = sorted(list(pages_dir.glob("*.jpg")))
        if not image_files:
            error_msg = "No images found to process"
            logger.error(f"❌ {error_msg}")
            state.set_error(error_msg, "process_imgs")
            return state
            
        verified_images = []
        for img_path in image_files:
            try:
                with Image.open(img_path) as img:
                    img.verify()
                verified_images.append(img_path)
            except Exception as e:
                logger.warning(f"Skipping unreadable image {img_path.name}: {str(e)}")
                
        if not verified_images:
            error_msg = "No valid images found to process"
            logger.error(f"❌ {error_msg}")
            state.set_error(error_msg, "process_imgs")
            return state
            
        logger.info(f"✓ Found {len(verified_images)} images to process")
        
        # Process images in batches
        all_metadata = []
        for i in range(0, len(verified_images), BATCH_SIZE):
            batch = verified_images[i:i + BATCH_SIZE]
            batch_metadata = await process_image_batch(batch, state, i)
            all_metadata.extend(batch_metadata)
            
            # Save state after each batch
            state.page_metadata = sorted(all_metadata, key=lambda x: x.page_number)
            # Initialize empty page_summaries dictionary with PageSummary objects
            state.page_summaries = {
                meta.page_number: PageSummary(
                    page_number=meta.page_number,
                    page_name=meta.page_name,
                    title=meta.descriptive_title,
                    file_path=meta.file_path
                ) for meta in all_metadata
            }
            await save_state(state, state.metadata.deck_id)
            
            # Add a small delay between batches
            await asyncio.sleep(0.5)
        
        # Update state with processed metadata
        state.page_metadata = sorted(all_metadata, key=lambda x: x.page_number)
        
        # Move to next stage (PROCESS)
        state.update_stage(WorkflowStage.PROCESS)
        state.set_stage_progress(
            total=3,
            completed=3,
            current=f"Completed processing {len(state.page_metadata)} images"
        )
        
        # Log completion
        log_state_change(
            state=state,
            node_name="process_imgs",
            change_type="complete",
            details={
                "total_pages": len(state.page_metadata),
                "deck_id": state.metadata.deck_id,
                "next_stage": WorkflowStage.PROCESS
            }
        )
        
        # Save state before handoff
        await save_state(state, state.metadata.deck_id)
        logger.info(f"State saved with {len(state.page_metadata)} pages ready for summary processing")
        
        return state
        
    except Exception as e:
        error_msg = f"Image processing failed: {str(e)}"
        log_error("process_imgs", error_msg)
        state.set_error(error_msg, "process_imgs")
        return state 