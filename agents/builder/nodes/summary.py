"""Summary processing node for extracting and processing page summaries."""
import logging
import traceback
from typing import List, Dict, Any, Tuple
from pathlib import Path
from langchain.prompts import ChatPromptTemplate
import asyncio
import base64
import os
import json
import re

from ..state import BuilderState, PageMetadata, PageSummary
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..prompts.summary_analysis_prompts import (
    SUMMARY_ANALYSIS_SYSTEM_PROMPT,
    SUMMARY_ANALYSIS_HUMAN_PROMPT
)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BATCH_SIZE = 5

def get_page_metadata(state: BuilderState) -> List[PageMetadata]:
    """Get metadata for each page from state."""
    try:
        if not state.page_metadata:
            logger.warning("No metadata available")
            return []
            
        return state.page_metadata
        
    except Exception as e:
        logger.error("Failed to retrieve metadata")
        return []

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

def sanitize_filename(title: str) -> str:
    """Convert a title to a valid filename.
    
    Args:
        title: The title to convert
        
    Returns:
        A sanitized filename
    """
    # Remove any characters that aren't alphanumeric, spaces, or dashes
    sanitized = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Ensure the filename isn't too long (max 100 chars)
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + "..."
    return sanitized.lower()

def rename_image_file(image_path: Path, new_name: str) -> Path:
    """Rename an image file with a new descriptive name.
    
    Args:
        image_path: Current path of the image
        new_name: New descriptive name for the file
        
    Returns:
        New path of the renamed file
    """
    # Get the file extension
    extension = image_path.suffix
    
    # Create the new filename
    new_filename = f"{new_name}{extension}"
    new_path = image_path.parent / new_filename
    
    # Rename the file
    image_path.rename(new_path)
    
    return new_path

async def create_summary_chain():
    """Create the chain for generating page summaries."""
    # Use centralized LLM configuration with JSON response format
    llm = await get_llm(
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    # Create prompt template with proper message structure
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUMMARY_ANALYSIS_SYSTEM_PROMPT),
        ("human", [
            {"type": "text", "text": "Please analyze this slide."},
            {"type": "image_url", "image_url": "{image_url}"}
        ])
    ])
    
    # Create chain
    chain = prompt | llm
    
    return chain

async def process_image_batch(
    batch: List[Tuple[Path, int]],
    chain,
    state: BuilderState
) -> Tuple[List[PageSummary], List[Dict]]:
    """Process a batch of images concurrently."""
    async def process_single_image(image_path: Path, page_num: int) -> Tuple[PageSummary, Dict, Path]:
        try:
            # Encode image - base64 data should not be logged
            image_url = encode_image_to_base64(str(image_path))
            
            # Generate summary with properly formatted input
            response = await chain.ainvoke({
                "image_url": image_url
            })
            
            # Clear the image data from memory explicitly
            del image_url
            
            # Parse response content directly since it's already JSON
            result = response if isinstance(response, dict) else json.loads(response.content)
            
            # Sanitize the title for filename
            sanitized_title = sanitize_filename(result["page_title"])
            
            # Add page number prefix for proper ordering
            file_prefix = f"{page_num:03d}"
            new_filename = f"{file_prefix}_{sanitized_title}"
            
            # Rename the image file
            new_path = rename_image_file(image_path, new_filename)
            
            # Create raw summary for storage (no image data)
            raw_summary = {
                "title": result["page_title"],
                "summary": result["summary"],
                "tableDetails": result["tableDetails"],
                "page": page_num,
                "file_path": str(new_path)
            }
            
            # Create summary for state
            summary = PageSummary(
                page_number=page_num,
                page_name=result["page_title"],
                file_path=str(new_path),  # Set the file path here
                summary=result["summary"],
                key_points=[],
                action_items=[],
                has_tables=result["tableDetails"]["hasBenefitsTable"],
                has_limitations=result["tableDetails"]["hasLimitations"]
            )
            
            logger.info(f"Processed page {page_num} - {new_filename}")
            return summary, raw_summary, new_path
            
        except Exception as e:
            logger.error(f"Failed to process page {page_num}")
            logger.error(traceback.format_exc())
            return None, None, None

    # Process batch concurrently
    tasks = [process_single_image(img_path, page_num) for img_path, page_num in batch]
    results = await asyncio.gather(*tasks)
    
    # Split results into summaries and raw data, filtering out None values
    summaries = []
    raw_summaries = []
    new_paths = []
    for summary, raw_summary, new_path in results:
        if summary and raw_summary and new_path:
            summaries.append(summary)
            raw_summaries.append(raw_summary)
            new_paths.append(new_path)
    
    return summaries, raw_summaries

async def process_summaries(state: BuilderState) -> BuilderState:
    """Process summaries for all pages."""
    try:
        if not state.deck_info or not state.deck_info.path:
            logger.error("Missing deck_info in state")
            return state
            
        # Get image directory
        pages_dir = Path(state.deck_info.path) / "img" / "pages"
        if not pages_dir.exists():
            logger.error(f"Pages directory not found: {pages_dir}")
            return state
            
        # Get all images and ensure proper sorting
        image_files = []
        jpg_files = sorted(pages_dir.glob("*.jpg"))
        png_files = sorted(pages_dir.glob("*.png"))
        image_files.extend(jpg_files)
        image_files.extend(png_files)
        
        if not image_files:
            logger.error(f"No image files found in {pages_dir}")
            return state
            
        logger.info(f"Starting summary processing for {len(image_files)} pages")
        logger.info(f"First few files: {[f.name for f in image_files[:3]]}...")
        
        # Create summary chain
        chain = await create_summary_chain()
        
        # Process images in batches
        all_summaries = []
        all_raw_summaries = []
        total_batches = (len(image_files) + BATCH_SIZE - 1) // BATCH_SIZE
        
        try:
            for i in range(0, len(image_files), BATCH_SIZE):
                batch_files = image_files[i:i + BATCH_SIZE]
                # Use absolute page numbers based on position in full list
                batch = [(img, i + idx + 1) for idx, img in enumerate(batch_files)]
                current_batch = i // BATCH_SIZE + 1
                
                logger.info(f"Processing batch {current_batch}/{total_batches}")
                logger.info(f"Batch files: {[f.name for f in batch_files]}")
                
                try:
                    summaries, raw_summaries = await process_image_batch(batch, chain, state)
                    if summaries and raw_summaries:
                        all_summaries.extend(summaries)
                        all_raw_summaries.extend(raw_summaries)
                        logger.info(f"Batch {current_batch} complete - processed {len(summaries)} summaries")
                        for s in summaries:
                            logger.info(f"  - Page {s.page_number}: {s.page_name}")
                    else:
                        logger.error(f"Batch {current_batch} failed to process")
                except Exception as batch_error:
                    logger.error(f"Error in batch {current_batch}: {str(batch_error)}")
                    logger.error(traceback.format_exc())
                    continue  # Continue with next batch
        except Exception as batch_loop_error:
            logger.error(f"Error in batch processing loop: {str(batch_loop_error)}")
            logger.error(traceback.format_exc())
            
        if not all_summaries:
            logger.error("No summaries were generated")
            return state
            
        # Sort summaries by page number
        all_summaries.sort(key=lambda x: x.page_number)
        all_raw_summaries.sort(key=lambda x: x["page"])
        
        logger.info(f"Summary generation complete. Generated {len(all_summaries)} summaries")
        pages_with_tables = [s.page_number for s in all_summaries if s.has_tables]
        logger.info(f"Pages with tables: {pages_with_tables}")
        
        # Update state with summaries
        state.page_summaries = all_summaries
        
        # Update page metadata with new file paths
        new_metadata = []
        for summary in all_summaries:
            metadata = PageMetadata(
                page_number=summary.page_number,
                page_name=summary.page_name,
                file_path=summary.file_path,
                content_type="slide"
            )
            new_metadata.append(metadata)
            logger.info(f"Added metadata for page {metadata.page_number}: {metadata.file_path}")
            
        state.page_metadata = new_metadata
        
        # Save raw summaries for downstream processing
        try:
            summaries_dir = Path(state.deck_info.path) / "ai"
            summaries_dir.mkdir(parents=True, exist_ok=True)
            summaries_path = summaries_dir / "summaries.json"
            with open(summaries_path, "w") as f:
                json.dump(all_raw_summaries, f, indent=2)
                
            logger.info(f"Saved {len(all_raw_summaries)} summaries to {summaries_path}")
            logger.info(f"State updated with {len(state.page_summaries)} summaries and {len(state.page_metadata)} metadata entries")
        except Exception as save_error:
            logger.error(f"Failed to save summaries: {str(save_error)}")
            logger.error(traceback.format_exc())
            # Continue since we still have the summaries in state
        
        # Validate final state
        if not state.page_summaries or not state.page_metadata:
            logger.error("Final state validation failed - missing summaries or metadata")
            return state
            
        return state
        
    except Exception as e:
        logger.error(f"Summary processing failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return state 