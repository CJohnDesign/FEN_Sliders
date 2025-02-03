"""Content parsing utilities for the builder agent."""
import logging
from typing import List, Optional
from pydantic import BaseModel
from ..state import BuilderState, SlideContent, PageSummary

# Set up logging
logger = logging.getLogger(__name__)

class Section(BaseModel):
    """Section of content with metadata."""
    title: str
    content: str
    start_line: int
    end_line: int
    metadata: Optional[dict] = None

def parse_script_sections(script: str) -> List[Section]:
    """Parse script content into sections."""
    sections = []
    current_section = None
    current_lines = []
    start_line = 0
    
    for i, line in enumerate(script.split('\n')):
        # Check for section marker (---- Title ----)
        if line.strip().startswith('----') and line.strip().endswith('----'):
            # Save previous section if exists
            if current_section:
                sections.append(Section(
                    title=current_section,
                    content='\n'.join(current_lines),
                    start_line=start_line,
                    end_line=i
                ))
                
            # Start new section
            current_section = line.strip()[4:-4].strip()
            current_lines = []
            start_line = i
        else:
            current_lines.append(line)
            
    # Add final section
    if current_section and current_lines:
        sections.append(Section(
            title=current_section,
            content='\n'.join(current_lines),
            start_line=start_line,
            end_line=len(script.split('\n'))
        ))
        
    return sections

def parse_slides_sections(slides: str) -> List[Section]:
    """Parse slides content into sections."""
    sections = []
    current_section = None
    current_lines = []
    start_line = 0
    
    for i, line in enumerate(slides.split('\n')):
        # Check for section marker (## Title)
        if line.strip().startswith('## '):
            # Save previous section if exists
            if current_section:
                sections.append(Section(
                    title=current_section,
                    content='\n'.join(current_lines),
                    start_line=start_line,
                    end_line=i
                ))
                
            # Start new section
            current_section = line.strip()[3:].strip()
            current_lines = []
            start_line = i
        else:
            current_lines.append(line)
            
    # Add final section
    if current_section and current_lines:
        sections.append(Section(
            title=current_section,
            content='\n'.join(current_lines),
            start_line=start_line,
            end_line=len(slides.split('\n'))
        ))
        
    return sections

def update_state_with_content(state: BuilderState) -> BuilderState:
    """Update state with parsed content sections."""
    try:
        # Parse script if available
        if state.script:
            script_sections = parse_script_sections(state.script)
            logger.info(f"Parsed {len(script_sections)} script sections")
            
            # Create structured content
            for section in script_sections:
                summary = PageSummary(
                    page_number=len(state.page_summaries) + 1,
                    page_name=section.title,
                    summary=section.content,
                    key_points=[],
                    action_items=[]
                )
                state.page_summaries.append(summary)
                
        # Parse slides if available
        if state.slides:
            slides_sections = parse_slides_sections(state.slides)
            logger.info(f"Parsed {len(slides_sections)} slide sections")
            
            # Create structured content
            for section in slides_sections:
                slide = SlideContent(
                    page_number=len(state.structured_slides) + 1,
                    title=section.title,
                    content=section.content
                )
                state.structured_slides.append(slide)
                
        return state
        
    except Exception as e:
        logger.error(f"Error parsing content: {str(e)}")
        state.error_context = {
            "error": str(e),
            "stage": "content_parsing"
        }
        return state 