"""Process slides node for generating presentation slides."""
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from langchain.prompts import ChatPromptTemplate
from ..state import BuilderState, WorkflowStage, SlideContent
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..prompts.slides_writer_prompts import (
    SLIDES_WRITER_SYSTEM_PROMPT,
    SLIDES_WRITER_HUMAN_PROMPT
)

# Set up logging
logger = logging.getLogger(__name__)

def get_template(state: BuilderState) -> str:
    """Get the slides template from state.
    
    Args:
        state: The current builder state containing template content
        
    Returns:
        str: The template content or empty string if not found
    """
    try:
        if not state.slides:
            logger.error("No template content found in state")
            return ""
            
        return state.slides
        
    except Exception as e:
        logger.error(f"Error accessing template from state: {str(e)}")
        return ""

async def process_slides(state: BuilderState) -> BuilderState:
    """Process content into slides."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.PROCESS_SLIDES:
            logger.warning(f"Expected stage {WorkflowStage.PROCESS_SLIDES}, but got {state.current_stage}")
            
        # Check for processed summaries
        if not state.processed_summaries:
            logger.error("No processed summaries found in state")
            state.error_context = {
                "error": "No processed summaries available",
                "stage": "process_slides"
            }
            return state
            
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", SLIDES_WRITER_SYSTEM_PROMPT),
            ("human", SLIDES_WRITER_HUMAN_PROMPT.format(
                template=state.slides, 
                processed_summaries=state.processed_summaries
            ))
        ])
        
        # Create and execute the chain
        llm = await get_llm(temperature=0.2)
        chain = prompt | llm
        
        # Generate slides
        logger.info("Generating slides content...")
        response = await chain.ainvoke({})
        slides_content = response.content
        
        # Write slides to file and update state
        output_path = Path(state.deck_info.path) / "slides.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(slides_content)
            
        # Create structured slides
        structured_slides = []
        sections = slides_content.split("---")
        for i, section in enumerate(sections):
            if section.strip():
                # Extract title from the section if it exists
                lines = section.strip().split("\n")
                title = next((line.replace("#", "").strip() for line in lines if line.startswith("#")), f"Slide {i + 1}")
                
                slide = SlideContent(
                    page_number=i + 1,
                    title=title,
                    content=section.strip()
                )
                structured_slides.append(slide)
        
        # Update state with generated content
        state.slides = slides_content
        state.structured_slides = structured_slides
        state.slide_count = len(structured_slides)
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="process_slides",
            change_type="complete",
            details={
                "slide_count": len(structured_slides),
                "output_path": str(output_path)
            }
        )
        
        # Update workflow stage
        state.update_stage(WorkflowStage.PROCESS_SLIDES)
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "process_slides", e)
        state.error_context = {
            "error": str(e),
            "stage": "process_slides"
        }
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 