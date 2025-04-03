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
    """Get the slides template from state or file.
    
    Args:
        state: The current builder state containing template content
        
    Returns:
        str: The template content or empty string if not found
    """
    try:
        # Try to read template from file
        if state.deck_info and state.deck_info.path:
            template_path = Path(state.deck_info.path) / "slides.md"
            if template_path.exists():
                logger.info(f"Reading template from {template_path}")
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
            
        # Get template and processed summaries
        template = get_template(state)
        if not template:
            error_msg = "Failed to get slides template"
            logger.error(error_msg)
            state.set_error(error_msg, "setup_slides")
            return state
            
        # Get processed summaries with fallback to aggregated content
        processed_summaries = state.processed_summaries
        if not processed_summaries and state.aggregated_content:
            logger.info("Using aggregated content as fallback for processed summaries")
            processed_summaries = state.aggregated_content
            
        if not processed_summaries:
            error_msg = "No processed summaries or aggregated content found"
            logger.error(error_msg)
            state.set_error(error_msg, "setup_slides")
            return state

        # Prepare metadata for template variables
        metadata = {
            "deck_key": state.metadata.deck_id,
            "title": state.metadata.title if state.metadata.title else state.metadata.deck_id
        }
        
        # Create chat prompt for slide generation
        prompt = ChatPromptTemplate.from_messages([
            ("system", SLIDES_WRITER_SYSTEM_PROMPT),
            ("human", SLIDES_WRITER_HUMAN_PROMPT.format(
                template=template,
                processed_summaries=processed_summaries,
                metadata=metadata
            ))
        ])
        
        # Get LLM response with higher temperature for more creative content
        llm = await get_llm(temperature=0.4)
        formatted_prompt = await prompt.ainvoke({
            "template": template,
            "processed_summaries": processed_summaries,
            "metadata": metadata
        })
        
        # Log prompt details for debugging
        logger.debug(f"Sending prompt with metadata: {metadata}")
        
        response = await llm.ainvoke(formatted_prompt)
        slides_content = response.content
        
        # Validate slides content
        if not slides_content or "{{" in slides_content:
            error_msg = "Generated slides content contains unresolved template variables"
            logger.error(error_msg)
            state.set_error(error_msg, "setup_slides")
            return state
        
        # Process slides content
        if slides_content:
            state.slides_content = slides_content  # Store in slides_content field
            
            # Save slides content
            if state.deck_info and state.deck_info.path:
                output_path = Path(state.deck_info.path) / "slides.md"
                success = await save_slides_to_file(slides_content, output_path)
                if not success:
                    error_msg = "Failed to save slides content"
                    logger.error(error_msg)
                    state.set_error(error_msg, "setup_slides")
                    return state
                    
                logger.info(f"Successfully saved slides to {output_path}")
                
            # Update state
            state = await save_state(state, state.metadata.deck_id)
            logger.info("Completed slide processing")
            
            # Log completion with detailed metrics
            log_state_change(
                state=state,
                node_name="setup_slides",
                change_type="complete",
                details={
                    "slides_content_length": len(slides_content),
                    "template_variables_resolved": "{{" not in slides_content,
                    "metadata_used": metadata
                }
            )
            
            return state
        else:
            error_msg = "Failed to generate slides content"
            logger.error(error_msg)
            state.set_error(error_msg, "setup_slides")
            return state
            
    except Exception as e:
        error_msg = f"Error in setup_slides: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "setup_slides")
        return state 