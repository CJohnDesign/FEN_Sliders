"""Script writer node for generating presentation script."""
import logging
from pathlib import Path
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from ..state import BuilderState
from ..utils.logging_utils import log_state_change, log_error

# Set up logging
logger = logging.getLogger(__name__)

def create_script_chain():
    """Create the chain for generating script content."""
    # Use a more capable model for script generation
    llm = ChatOpenAI(
        model="gpt-4-0125-preview",
        temperature=0.2,
        request_timeout=120
    )
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_template(
        """Generate a presentation script from the following slides content.
        The script should:
        1. Flow naturally between sections
        2. Expand on slide content with details
        3. Include clear transitions
        4. Use professional but conversational tone
        5. Include timing markers
        
        Slides Content:
        {content}
        
        Format the script to be clear and well-structured."""
    )
    
    # Create chain
    chain = prompt | llm
    
    return chain

async def script_writer(state: BuilderState) -> BuilderState:
    """Generate script content."""
    try:
        # Check for slides content
        if not state.slides:
            logger.warning("No slides content found in state")
            state.error_context = {
                "error": "No slides content available",
                "stage": "script_writing"
            }
            return state
            
        # Create script chain
        chain = create_script_chain()
        
        # Generate script content
        script_content = await chain.ainvoke({"content": state.slides})
        
        # Write script to file
        output_path = Path(state.deck_info.path) / "script.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(script_content)
            
        # Update state
        state.script = script_content
        
        # Log completion
        log_state_change(
            state=state,
            node_name="script_writer",
            change_type="complete",
            details={"output_path": str(output_path)}
        )
        
        return state
        
    except Exception as e:
        log_error(state, "script_writer", e)
        state.error_context = {
            "error": str(e),
            "stage": "script_writing"
        }
        return state 