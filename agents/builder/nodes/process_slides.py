"""Process slides node for generating slide content."""
import logging
from pathlib import Path
from typing import List, Dict, Any
from ..state import BuilderState, SlideContent
from ..utils.logging_utils import log_state_change, log_error

# Set up logging
logger = logging.getLogger(__name__)

def count_slides(content: str) -> int:
    """Count the number of slides in the content."""
    return content.count('---') // 2

async def process_slides(state: BuilderState) -> BuilderState:
    """Process content into slides."""
    try:
        # Check for required state
        if not state.processed_summaries:
            logger.error("No processed summaries found in state")
            state.error_context = {
                "error": "No processed summaries available",
                "stage": "slide_processing"
            }
            return state
            
        logger.info("Processing aggregated summaries into slides")
            
        # Get output path
        output_path = Path(state.deck_info.path) / "slides.md"
        
        # Generate slides content using processed summaries
        slides_content = state.processed_summaries
        
        # Write slides to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(slides_content)
            
        # Update state
        state.slides = slides_content
        state.slide_count = count_slides(slides_content)
        
        # Create structured slides from processed summaries
        structured_slides = []
        sections = slides_content.split("---")
        for i, section in enumerate(sections):
            if section.strip():
                slide = SlideContent(
                    page_number=i + 1,
                    title=f"Slide {i + 1}",
                    content=section.strip()
                )
                structured_slides.append(slide)
                
        state.structured_slides = structured_slides
        
        logger.info(f"Generated {state.slide_count} slides")
        logger.info(f"Slides saved to {output_path}")
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to process slides: {str(e)}")
        state.error_context = {
            "error": str(e),
            "stage": "slide_processing"
        }
        return state 