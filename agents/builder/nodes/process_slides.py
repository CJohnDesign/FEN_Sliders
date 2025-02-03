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
        # Check for processed content
        if not state.processed_content:
            logger.warning("No processed content found in state")
            state.error_context = {
                "error": "No processed content available",
                "stage": "slide_processing"
            }
            return state
            
        # Get template and output paths
        base_dir = Path(__file__).parent.parent.parent.parent
        template_path = base_dir / "decks" / state.metadata.template / "slides.md"
        output_path = Path(state.deck_info.path) / "slides.md"
        
        # Read template
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found at {template_path}")
            
        with open(template_path) as f:
            template = f.read()
            
        # Get page metadata
        pages_with_tables = []
        pages_with_limitations = []
        if state.page_summaries:
            for summary in state.page_summaries:
                if summary.has_tables:
                    pages_with_tables.append(summary.page_number)
                if summary.has_limitations:
                    pages_with_limitations.append(summary.page_number)
        
        # Generate slides content
        slides_content = template.format(
            title=state.metadata.title,
            content=state.processed_content,
            tables=", ".join(map(str, pages_with_tables)),
            limitations=", ".join(map(str, pages_with_limitations))
        )
        
        # Write slides to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(slides_content)
            
        # Update state
        state.slides = slides_content
        state.slide_count = count_slides(slides_content)
        
        # Create structured slides
        structured_slides = []
        for summary in state.page_summaries:
            slide = SlideContent(
                page_number=summary.page_number,
                title=summary.page_name,
                content=summary.summary,
                has_tables=summary.has_tables,
                has_limitations=summary.has_limitations
            )
            structured_slides.append(slide)
            
        state.structured_slides = structured_slides
        
        # Log completion
        log_state_change(
            state=state,
            node_name="process_slides",
            change_type="complete",
            details={
                "slide_count": state.slide_count,
                "output_path": str(output_path)
            }
        )
        
        return state
        
    except Exception as e:
        log_error(state, "process_slides", e)
        state.error_context = {
            "error": str(e),
            "stage": "slide_processing"
        }
        return state 