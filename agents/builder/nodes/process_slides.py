"""Process slides node for generating presentation slides."""
import logging
import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain.prompts import ChatPromptTemplate
from langsmith import Client, trace
from langsmith.run_helpers import traceable
from ..state import BuilderState, WorkflowStage, SlideContent
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ...utils.content import save_content
from ..prompts.slides_writer_prompts import (
    SLIDES_WRITER_SYSTEM_PROMPT,
    SLIDES_WRITER_HUMAN_PROMPT
)

# Set up logging and LangSmith client
logger = logging.getLogger(__name__)
ls_client = Client()

class SlideState(BaseModel):
    """State for slide generation."""
    processed_summaries: str = Field(default="")  # Default to empty string
    template: str = Field(default="")  # Default to empty string
    slides_content: Optional[str] = Field(default=None)
    structured_slides: List[SlideContent] = Field(default_factory=list)

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
            
            # Get processed summaries with fallback
            processed_summaries = ""
            if hasattr(state, 'processed_summaries') and state.processed_summaries:
                processed_summaries = state.processed_summaries
            else:
                logger.warning("No processed summaries found in state")
            
            # Initialize slide state
            slide_state = SlideState(
                processed_summaries=processed_summaries,
                template=template
            )
            
            # Verify we're in the correct stage and fix if needed
            if state.current_stage != WorkflowStage.PROCESS_SLIDES:
                logger.warning(f"Expected stage {WorkflowStage.PROCESS_SLIDES}, but got {state.current_stage}")
                state.update_stage(WorkflowStage.PROCESS_SLIDES)
                
            # Validate required state attributes
            if not processed_summaries:
                error_msg = "Missing processed summaries"
                logger.error(error_msg)
                state.set_error(error_msg, "process_slides")
                return state
            
            logger.info("All required attributes present")
            logger.info(f"Processed summaries length: {len(state.processed_summaries)}")
            
            # Create prompt template
            logger.info("Creating slide generation prompt...")
            prompt = ChatPromptTemplate.from_messages([
                ("system", SLIDES_WRITER_SYSTEM_PROMPT),
                ("human", SLIDES_WRITER_HUMAN_PROMPT.format(
                    template=slide_state.template,
                    processed_summaries=slide_state.processed_summaries
                ))
            ])
            
            # Create and execute the chain
            logger.info("Initializing LLM for slide generation...")
            llm = await get_llm(temperature=0.2)
            chain = prompt | llm
            
            # Generate slides
            logger.info("Generating slides content...")
            try:
                # Track the LLM call with LangSmith
                with trace(name="llm_slide_generation") as llm_trace:
                    response = await chain.ainvoke({})
                    llm_trace.metadata["model"] = "gpt4o"
                    llm_trace.metadata["temperature"] = 0.2
                    
                slide_state.slides_content = response.content
                logger.info(f"Generated slides content length: {len(slide_state.slides_content)}")
            except Exception as gen_error:
                logger.error(f"Error during slide generation: {str(gen_error)}")
                state.set_error(
                    "Failed to generate slides content",
                    "process_slides",
                    {"error": str(gen_error)}
                )
                return state
            
            # Validate slides content
            if not slide_state.slides_content or not slide_state.slides_content.strip():
                logger.error("Generated slides content is empty")
                state.set_error(
                    "Generated slides content is empty",
                    "process_slides"
                )
                return state
                
            # Save slides to file
            output_path = Path(state.deck_info.path) / "slides.md"
            logger.info(f"Attempting to save slides to {output_path}")
            if not await save_slides_to_file(slide_state.slides_content, output_path):
                state.set_error(
                    "Failed to save slides to file",
                    "process_slides",
                    {"path": str(output_path)}
                )
                return state
                
            # Create structured slides
            logger.info("Creating structured slides...")
            sections = slide_state.slides_content.split("---")
            logger.info(f"Found {len(sections)} slide sections")
            
            structured_slides = []
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
                    logger.info(f"Processed slide {i + 1}: {title}")
            
            slide_state.structured_slides = structured_slides
            
            # Validate structured slides
            if not slide_state.structured_slides:
                logger.error("No structured slides were created")
                state.set_error(
                    "Failed to create structured slides",
                    "process_slides"
                )
                return state
            
            # Update state with generated content
            state.slides = slide_state.slides_content
            state.structured_slides = slide_state.structured_slides
            state.slide_count = len(slide_state.structured_slides)
            logger.info(f"Successfully created {len(slide_state.structured_slides)} structured slides")
            
            # Add metadata about the slide generation process
            slide_trace.metadata.update({
                "deck_id": state.metadata.deck_id if state.metadata else None,
                "slides_content_length": len(slide_state.slides_content),
                "num_slides": len(slide_state.structured_slides),
                "output_path": str(output_path)
            })
            
            # Log completion and update stage
            log_state_change(
                state=state,
                node_name="process_slides",
                change_type="complete",
                details={
                    "slide_count": len(slide_state.structured_slides),
                    "output_path": str(output_path),
                    "slides_content_length": len(slide_state.slides_content),
                    "structured_slides_count": len(slide_state.structured_slides)
                }
            )
            
            # Save state before transitioning
            if state.metadata and state.metadata.deck_id:
                save_state(state, state.metadata.deck_id)
                logger.info(f"Saved state for deck {state.metadata.deck_id}")
            
            # Update workflow stage
            state.update_stage(WorkflowStage.SETUP_AUDIO)
            logger.info(f"Moving to next stage: {state.current_stage}")
            
            # Save state again after stage transition
            if state.metadata and state.metadata.deck_id:
                save_state(state, state.metadata.deck_id)
            
            return state
            
    except Exception as e:
        logger.error(f"Error in process_slides: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        state.set_error(
            str(e),
            "process_slides",
            {
                "error_type": type(e).__name__,
                "stage": "process_slides",
                "current_stage": str(state.current_stage)
            }
        )
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 