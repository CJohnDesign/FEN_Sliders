"""Page separator node for processing slides and script content."""
import re
import logging
from typing import List, Dict, Optional
from pydantic import BaseModel
from ..state import BuilderState, WorkflowStage
from ..utils.state_utils import save_state
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from langchain.prompts import ChatPromptTemplate

# Set up logging
logger = logging.getLogger(__name__)

class PageContent(BaseModel):
    """Model for page content containing slide and script information."""
    slide: Dict[str, str] = {"header": "", "content": ""}
    script: Dict[str, str] = {"header": "", "content": ""}

class Pages(BaseModel):
    """Model for pages collection."""
    pages: List[PageContent] = []

def parse_slide_content(content: str) -> List[Dict[str, str]]:
    """Parse slide content into list of slides with headers and content.
    
    Args:
        content: Raw slide content string
        
    Returns:
        List of dictionaries containing header and content for each slide
    """
    # Split content by slide separator
    slides = content.split("\n---\n")
    parsed_slides = []
    
    for slide in slides:
        if not slide.strip():
            continue
            
        # Split into header and content if header exists
        parts = slide.split("\n---\n", 1)
        if len(parts) > 1:
            header, content = parts
        else:
            header = ""
            content = parts[0]
            
        parsed_slides.append({
            "header": header.strip(),
            "content": content.strip()
        })
        
    return parsed_slides

def parse_script_content(content: str) -> List[Dict[str, str]]:
    """Parse script content into list of sections with headers and content.
    
    Args:
        content: Raw script content string
        
    Returns:
        List of dictionaries containing header and content for each section
    """
    # Split by script section separator (4 or more dashes with text in between)
    sections = re.split(r'[-]{4,}\s*([^-]+?)\s*[-]{4,}', content)
    parsed_sections = []
    
    # Process sections (skip first if empty)
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            header = sections[i].strip()
            content = sections[i + 1].strip()
            parsed_sections.append({
                "header": header,
                "content": content
            })
            
    return parsed_sections

async def page_separator(state: BuilderState) -> BuilderState:
    """Process slides and script content into structured page objects.
    
    Args:
        state: Current builder state
        
    Returns:
        Updated builder state with structured pages
    """
    try:
        logger.info("Starting page separation process")
        
        # Validate required state attributes
        if not state.slides or not state.script:
            error_msg = "Missing required content"
            logger.error(error_msg)
            state.set_error(error_msg, "page_separator")
            return state
            
        # Parse slides and script
        slides = parse_slide_content(state.slides)
        scripts = parse_script_content(state.script)
        
        logger.info(f"Found {len(slides)} slides and {len(scripts)} script sections")
        
        # Create pages collection
        pages = Pages()
        
        # Match slides with scripts
        # Assuming 1-to-1 correspondence between slides and script sections
        for i in range(max(len(slides), len(scripts))):
            page = PageContent()
            
            # Add slide content if available
            if i < len(slides):
                page.slide = slides[i]
                
            # Add script content if available
            if i < len(scripts):
                page.script = scripts[i]
                
            pages.pages.append(page)
            
        # Update state with structured pages
        state.structured_pages = pages.dict()
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="page_separator",
            change_type="complete",
            details={
                "total_pages": len(pages.pages),
                "slides_processed": len(slides),
                "scripts_processed": len(scripts)
            }
        )
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "page_separator", e)
        state.error_context = {
            "error": str(e),
            "stage": "page_separation"
        }
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 