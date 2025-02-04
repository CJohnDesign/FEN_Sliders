"""Slides writer node for generating presentation slides."""
import logging
from pathlib import Path
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, SlideContent
from ..utils.logging_utils import log_state_change, log_error
from ..config.models import get_model_config
from ...utils.llm_utils import get_llm
from ..prompts.summary_prompts import PROCESS_SLIDES_PROMPT, PROCESS_SLIDES_HUMAN_TEMPLATE

# Set up logging
logger = logging.getLogger(__name__)

def create_slides_chain():
    """Create the chain for generating slides content."""
    # Use centralized LLM configuration
    llm = get_llm(temperature=0.2)
    
    # Create prompt template using imported prompts
    prompt = ChatPromptTemplate.from_messages([
        ("system", PROCESS_SLIDES_PROMPT),
        ("human", PROCESS_SLIDES_HUMAN_TEMPLATE)
    ])
    
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
        slides_content = await chain.ainvoke({
            "template": state.deck_info.template,
            "processed_summaries": state.processed_summaries
        })
        
        # Write slides to file
        output_path = Path(state.deck_info.path) / "slides.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(slides_content.content)
            
        # Update state
        state.slides = slides_content.content
        
        # Create structured slides
        structured_slides = []
        sections = slides_content.content.split("---")
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