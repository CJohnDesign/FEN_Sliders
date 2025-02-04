"""Slides writer node for generating presentation slides."""
import logging
from pathlib import Path
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from ..state import BuilderState, SlideContent
from ..utils.logging_utils import log_state_change, log_error
from ..config.models import get_model_config
from ...utils.llm_utils import get_llm

# Set up logging
logger = logging.getLogger(__name__)

def create_slides_chain():
    """Create the chain for generating slides content."""
    # Use centralized LLM configuration
    llm = get_llm(temperature=0.2)
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_template(
        """Generate presentation slides from the following content.
        Follow these guidelines:
        1. Clear and concise points
        2. Consistent formatting
        3. Proper transitions
        4. Engaging visuals
        5. Professional tone
        
        Content:
        {content}
        
        Format the slides to be clear and well-structured."""
    )
    
    # Create chain
    chain = prompt | llm
    
    return chain

async def slides_writer(state: BuilderState) -> BuilderState:
    """Generate slides content."""
    try:
        # Check for processed content
        if not state.processed_summaries:
            logger.warning("No processed summaries found in state")
            state.error_context = {
                "error": "No processed summaries available",
                "stage": "slides_writing"
            }
            return state
            
        # Create slides chain
        chain = create_slides_chain()
        
        # Generate slides content
        slides_content = await chain.ainvoke({"content": state.processed_summaries})
        
        # Write slides to file
        output_path = Path(state.deck_info.path) / "slides.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(slides_content)
            
        # Update state
        state.slides = slides_content
        
        # Create structured slides
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
        
        # Log completion
        log_state_change(
            state=state,
            node_name="slides_writer",
            change_type="complete",
            details={
                "slide_count": len(structured_slides),
                "output_path": str(output_path)
            }
        )
        
        return state
        
    except Exception as e:
        log_error(state, "slides_writer", e)
        state.error_context = {
            "error": str(e),
            "stage": "slides_writing"
        }
        return state 