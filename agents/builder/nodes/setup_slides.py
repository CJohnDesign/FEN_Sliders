"""Process slides node for generating presentation slides."""
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from langchain.prompts import ChatPromptTemplate
from langsmith import Client, trace
from langsmith.run_helpers import traceable
from ..state import BuilderState, WorkflowStage, SlideContent, WorkflowProgress, StageProgress
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ...utils.content import save_content
from ..prompts.slides_writer_prompts import (
    SLIDES_WRITER_SYSTEM_PROMPT,
    SLIDES_WRITER_HUMAN_PROMPT
)
from datetime import datetime

# Set up logging and LangSmith client
logger = logging.getLogger(__name__)
ls_client = Client()

class SlideState(BaseModel):
    """State for slide generation."""
    processed_summaries: str = Field(default="")
    template: str = Field(default="")
    slides_content: Optional[str] = Field(default=None)
    structured_slides: List[SlideContent] = Field(default_factory=list)
    
    model_config = ConfigDict(
        extra='ignore',
        validate_assignment=True,
        str_strip_whitespace=True
    )

def get_template(state: BuilderState) -> str:
    """Get the slides template from state.
    
    Args:
        state: The current builder state containing template content
        
    Returns:
        str: The template content or empty string if not found
    """
    try:
        # Check if template exists in state
        if state.slides:
            return state.slides
            
        # Try to read template from file
        if state.deck_info and state.deck_info.path:
            template_path = Path(state.deck_info.path) / "slides.md"
            if template_path.exists():
                return template_path.read_text()
                
        logger.warning("No template found, using empty template")
        return ""
        
    except Exception as e:
        logger.error(f"Error accessing template: {str(e)}")
        return ""

@traceable(name="save_slides_to_file")
async def save_slides_to_file(slides_content: str, output_path: Path) -> bool:
    """Save slides content to file with proper error handling."""
    try:
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        await save_content(output_path, slides_content)
        logger.info(f"Successfully saved slides to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save slides to {output_path}: {str(e)}")
        return False

@traceable(name="process_slides")
async def process_slides(state: BuilderState) -> BuilderState:
    """Process content into slides."""
    try:
        with trace(name="slide_processing") as slide_trace:
            logger.info("Starting slide processing...")
            logger.info(f"Current stage: {state.current_stage}")
            
            # Get template
            template = get_template(state)
            logger.info(f"Template length: {len(template)}")
            
            # Define replacements
            replacements = {
                "{{deck_key}}": "FEN_EVE",
                "{{ Plan Name }}": "Everest",
                "{{ Plan Full Name }}": "Everest Insurance Benefits",
                "{{ Organization }}": "Everest Insurance",
                "{{ Brand }}": "Everest",
                "{{ Partner }}": "Everest Insurance Partners",
                "{{ Benefit Category 1 }}": "Risk Management",
                "{{ Benefit Category 2 }}": "Claims Support",
                "{{ Benefit Category 3 }}": "Customer Service",
                "{{ Benefit Category 4 }}": "Technical Support",
                "{{ Tool Name }}": "Risk Management Portal",
                "{{ Acronym }}": "RMP",
                "{{ Feature 1 }}": "Claims Management",
                "{{ Feature 2 }}": "Risk Assessment",
                "{{ Overview Point 1 }}": "Complete insurance solutions",
                "{{ Benefit Type 1 }}": "Property Insurance",
                "{{ Benefit Type 2 }}": "Casualty Insurance",
                "{{ Benefit Type 3 }}": "Specialty Insurance",
                "{{ Benefit Type 4 }}": "Risk Management Services",
                "{{ Additional Benefit }}": "24/7 Claims Support",
                "{{ Feature }}": "Online Portal"
            }
            
            # Replace variables in template
            processed_template = template
            for old, new in replacements.items():
                processed_template = processed_template.replace(old, new)
            
            # Get processed summaries with fallback
            processed_summaries = ""
            if hasattr(state, 'processed_summaries') and state.processed_summaries:
                processed_summaries = state.processed_summaries
            else:
                logger.warning("No processed summaries found in state")
            
            # Initialize slide state
            slide_state = SlideState(
                processed_summaries=processed_summaries,
                template=processed_template
            )
            
            # Verify we're in the correct stage and fix if needed
            if state.current_stage != WorkflowStage.PROCESS_SLIDES:
                logger.warning(f"Expected stage {WorkflowStage.PROCESS_SLIDES}, but got {state.current_stage}")
                state.current_stage = WorkflowStage.PROCESS_SLIDES
                
            # Create chat prompt for slide generation
            prompt = ChatPromptTemplate.from_messages([
                ("system", SLIDES_WRITER_SYSTEM_PROMPT),
                ("human", SLIDES_WRITER_HUMAN_PROMPT.format(
                    template=processed_template,
                    processed_summaries=processed_summaries
                ))
            ])
            
            # Get LLM response
            llm = get_llm()
            response = await llm.ainvoke(prompt)
            slides_content = response.content
            
            # Replace any remaining template variables in the response
            for old, new in replacements.items():
                slides_content = slides_content.replace(old, new)
            
            # Save slides content
            if state.deck_info and state.deck_info.path:
                output_path = Path(state.deck_info.path) / "slides.md"
                success = await save_slides_to_file(slides_content, output_path)
                if not success:
                    raise Exception("Failed to save slides content")
                    
                logger.info(f"Successfully saved slides to {output_path}")
                state.slides = slides_content
                
            # Update state
            state = await save_state(state)
            logger.info("Completed slide processing")
            return state
            
    except Exception as e:
        log_error("Error in process_slides", e)
        raise 

@traceable(name="setup_slides")
async def setup_slides(state: BuilderState) -> BuilderState:
    """Set up slides based on processed content."""
    try:
        logger.info("Starting slide setup")
        
        # Initialize workflow progress if not present
        if not state.workflow_progress:
            state.workflow_progress = WorkflowProgress(
                current_stage=WorkflowStage.GENERATE,
                stages={
                    WorkflowStage.GENERATE: StageProgress(
                        status="in_progress",
                        started_at=datetime.now().isoformat()
                    )
                }
            )
        
        # Verify we're in the correct stage
        if state.workflow_progress.current_stage != WorkflowStage.GENERATE:
            logger.warning(f"Expected stage {WorkflowStage.GENERATE}, got {state.workflow_progress.current_stage}")
            state.update_stage(WorkflowStage.GENERATE)
            
        # ... rest of the function implementation ...

        log_state_change(state, "setup_slides", "complete")
        return state

    except Exception as e:
        error_msg = f"Error in setup_slides: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "setup_slides")
        return state 