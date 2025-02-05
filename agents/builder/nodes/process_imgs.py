"""Image processing node for handling presentation images."""
import logging
import asyncio
import base64
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image
from io import BytesIO
from ..state import BuilderState, PageMetadata, WorkflowStage
from ..utils.logging_utils import log_error, log_state_change
from ..utils.state_utils import save_state
from ...utils.llm_utils import get_llm
from agents.utils.pdf_utils import convert_pdf_to_images
from langchain.prompts import ChatPromptTemplate
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BATCH_SIZE = 5

IMAGE_ANALYSIS_PROMPT = """You are an expert at analyzing presentation slides and extracting their content.
For this slide image, please:
1. Extract all visible text
2. Describe any visible diagrams, charts, or graphics
3. Note any key data points or statistics
4. Identify the main topic/purpose of the slide
5. Generate a descriptive name for this slide based on its content (use snake_case)

Return the information in this JSON format:
{
    "extracted_text": "All text found in the image",
    "visual_elements": "Description of diagrams/charts/graphics",
    "key_points": ["List of important points"],
    "main_topic": "Primary topic of the slide",
    "descriptive_name": "snake_case_name_for_slide"
}"""

@traceable(name="get_image_base64")
async def get_image_base64(image_path: Path) -> str:
    """Convert image to base64 string."""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # Resize if too large (max 2048px on longest side)
            max_size = 2048
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return img_str
    except Exception as e:
        logger.error(f"Error converting image to base64: {str(e)}")
        return ""

@traceable(name="analyze_image_with_gpt")
async def analyze_image_with_gpt(image_path: Path) -> Dict[str, Any]:
    """Analyze image content using GPT-4 Vision."""
    try:
        # Convert image to base64
        base64_image = await get_image_base64(image_path)
        if not base64_image:
            raise ValueError("Failed to convert image to base64")

        # Get LLM instance
        llm = await get_llm(model="gpt-4o", temperature=0.2)
        
        # Create messages for vision analysis
        messages = [
            {
                "role": "system",
                "content": IMAGE_ANALYSIS_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please analyze this slide image:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]
        
        # Call the vision model directly
        response = await llm.ainvoke(messages)
        
        # Parse response
        try:
            result = json.loads(response.content)
            return result
        except:
            # If not JSON, create structured response
            return {
                "extracted_text": response.content.strip(),
                "visual_elements": "",
                "key_points": [],
                "main_topic": "Unknown",
                "descriptive_name": image_path.stem
            }

    except Exception as e:
        logger.error(f"Error analyzing image with GPT: {str(e)}")
        return {"error": str(e)}

@traceable(name="process_image_batch")
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
                
            # Analyze image with GPT
            analysis = await analyze_image_with_gpt(image_path)
            
            if "error" in analysis:
                raise ValueError(f"Failed to analyze image: {analysis['error']}")
            
            # Create new page metadata with descriptive name
            descriptive_name = analysis.get("descriptive_name", image_path.stem)
            content = (
                f"Main Topic: {analysis.get('main_topic', '')}\n\n"
                f"Extracted Text:\n{analysis.get('extracted_text', '')}\n\n"
                f"Visual Elements:\n{analysis.get('visual_elements', '')}\n\n"
                f"Key Points:\n" + "\n".join(analysis.get('key_points', []))
            )
            
            metadata = PageMetadata(
                page_number=page_number,
                page_name=descriptive_name,
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
                    "file_path": str(image_path),
                    "descriptive_name": descriptive_name
                }
            )
            
            logger.info(f"✓ Processed image {page_number}: {descriptive_name}")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Error processing image {image_path.name}:")
            log_error("process_imgs", str(e))
            return None

    # Process batch concurrently
    tasks = [process_single_image(img, i) for i, img in enumerate(batch)]
    results = await asyncio.gather(*tasks)
    
    # Filter out failed results
    return [result for result in results if result is not None]

@traceable(name="process_imgs")
async def process_imgs(state: BuilderState) -> BuilderState:
    """Process images from PDF or existing files while preserving state."""
    try:
        logger.info("Starting process_imgs node")
        
        # Verify we're in the correct stage
        if state.workflow_progress.current_stage != WorkflowStage.EXTRACT:
            logger.warning(f"Expected stage {WorkflowStage.EXTRACT}, got {state.workflow_progress.current_stage}")
            state.update_stage(WorkflowStage.EXTRACT)
        
        # Check deck info exists
        if not state.deck_info:
            error_msg = "No deck info found in state"
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
            total=3,  # PDF conversion, image processing, finalization
            completed=0,
            current="Starting image processing"
        )
        
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
            
            state.set_stage_progress(
                total=3,
                completed=1,
                current="Converting PDFs to images"
            )
            
            # Convert PDFs to images
            await convert_pdf_to_images(pdf_files[0], pages_dir)
            
        # Get all image files
        image_files = sorted(list(pages_dir.glob("*.jpg")))
        if not image_files:
            error_msg = "No images found to process"
            logger.error(f"❌ {error_msg}")
            state.set_error(error_msg, "process_imgs")
            return state
            
        logger.info(f"✓ Found {len(image_files)} images to process")
        
        # Process images in batches
        existing_metadata = {meta.page_number: meta for meta in state.page_metadata} if state.page_metadata else {}
        all_metadata = []
        
        # Update progress for image processing
        state.set_stage_progress(
            total=3,
            completed=2,
            current=f"Processing {len(image_files)} images"
        )
        
        for i in range(0, len(image_files), BATCH_SIZE):
            batch = image_files[i:i + BATCH_SIZE]
            batch_metadata = await process_image_batch(batch, state, pages_dir, existing_metadata)
            all_metadata.extend(batch_metadata)
            
            # Update progress within batch processing
            progress = min((i + BATCH_SIZE) / len(image_files), 1.0)
            logger.info(f"Progress: {progress:.1%}")
        
        # Update state with processed metadata
        state.page_metadata = sorted(all_metadata, key=lambda x: x.page_number)
        
        # Move to next stage (PROCESS)
        state.update_stage(WorkflowStage.PROCESS)
        state.set_stage_progress(
            total=3,
            completed=3,
            current="Completed image processing"
        )
        
        # Save state
        await save_state(state, state.metadata.deck_id)
        return state
        
    except Exception as e:
        error_msg = f"Image processing failed: {str(e)}"
        log_error("process_imgs", error_msg)
        state.set_error(error_msg, "process_imgs")
        return state 