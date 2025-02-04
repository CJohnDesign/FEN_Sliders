"""Script writer node for generating presentation script."""
import logging
from pathlib import Path
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from ..state import BuilderState
from ..utils.logging_utils import log_state_change, log_error
from ..config.models import get_model_config
from ...utils.llm_utils import get_llm

# Set up logging
logger = logging.getLogger(__name__)

def create_script_chain():
    """Create the chain for generating script content."""
    # Use centralized LLM configuration
    llm = get_llm(temperature=0.2)
    
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
        # Check for processed content
        if not state.processed_summaries:
            logger.warning("No processed summaries found in state")
            state.error_context = {
                "error": "No processed summaries available",
                "stage": "script_writing"
            }
            return state
            
        # Create script chain
        chain = create_script_chain()
        
        # Generate script content
        script_content = await chain.ainvoke({"content": state.processed_summaries})
        
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