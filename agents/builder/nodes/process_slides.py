"""Process slides node for generating slide content."""
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, SlideContent, WorkflowStage
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..prompts.summary_prompts import PROCESS_SLIDES_PROMPT, PROCESS_SLIDES_HUMAN_TEMPLATE

# Set up logging
logger = logging.getLogger(__name__)

def get_template(template_path: Path) -> str:
    """Get the slides template from the template folder."""
    try:
        template_file = template_path / "slides.md"
        if not template_file.exists():
            logger.error(f"Template file not found: {template_file}")
            return ""
            
        with open(template_file) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading template: {str(e)}")
        return ""

async def process_slides(state: BuilderState) -> BuilderState:
    """Process content into slides."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.PROCESS_SLIDES:
            logger.warning(f"Expected stage {WorkflowStage.PROCESS_SLIDES}, but got {state.current_stage}")
        
        # Check for required state
        if not state.processed_summaries:
            logger.error("No processed summaries found in state")
            state.error_context = {
                "error": "No processed summaries available",
                "stage": "slide_processing"
            }
            return state
            
        # Validate the processed summaries content
        if not isinstance(state.processed_summaries, str) or len(state.processed_summaries.strip()) < 10:
            logger.error("Invalid or empty processed summaries content")
            state.error_context = {
                "error": "Invalid aggregated summary content",
                "stage": "slide_processing"
            }
            return state
            
        logger.info(f"Processing aggregated summaries into slides (content length: {len(state.processed_summaries)})")
        
        # Get template path
        base_dir = Path(__file__).parent.parent.parent.parent
        template_dir = base_dir / "decks" / state.deck_info.template
        
        # Get template from template folder
        template = get_template(template_dir)
        if not template:
            logger.error("No slides template available")
            state.error_context = {
                "error": "No slides template available",
                "stage": "slide_processing"
            }
            return state
        
        # Create system and human messages for the LLM
        system_message = SystemMessage(content=PROCESS_SLIDES_PROMPT)
        
        human_message = HumanMessage(content=PROCESS_SLIDES_HUMAN_TEMPLATE.format(
            template=template,
            processed_summaries=state.processed_summaries
        ))
        
        # Create and execute the chain
        prompt = ChatPromptTemplate.from_messages([system_message, human_message])
        llm = await get_llm(temperature=0.2)
        chain = prompt | llm
        
        # Generate the complete markdown
        logger.info("Generating complete slides markdown...")
        response = await chain.ainvoke({})
        slides_content = response.content
        
        # Write slides to file
        output_path = Path(state.deck_info.path) / "slides.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(slides_content)
            
        # Update state
        state.slides = slides_content
        state.slide_count = len(slides_content.split("---")) - 1  # -1 because split gives one more than separators
        
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
                
        state.structured_slides = structured_slides
        
        logger.info(f"Generated {state.slide_count} slides")
        logger.info(f"Slides saved to {output_path}")
        logger.info(f"First slide title: {structured_slides[0].title if structured_slides else 'No slides generated'}")
        
        # Log state change and update stage
        log_state_change(
            state=state,
            node_name="process_slides",
            change_type="complete",
            details={
                "slide_count": state.slide_count,
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
        logger.error(f"Failed to process slides: {str(e)}")
        state.error_context = {
            "error": str(e),
            "stage": "slide_processing"
        }
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 