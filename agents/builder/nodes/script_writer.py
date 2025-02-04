"""Script writer node for generating presentation script."""
import logging
from pathlib import Path
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState
from ..utils.logging_utils import log_state_change, log_error
from ..config.models import get_model_config
from ...utils.llm_utils import get_llm
from ..prompts.summary_prompts import SCRIPT_WRITER_PROMPT, SCRIPT_WRITER_HUMAN_TEMPLATE

# Set up logging
logger = logging.getLogger(__name__)

def create_script_chain():
    """Create the chain for generating script content."""
    # Use centralized LLM configuration
    llm = get_llm(temperature=0.2)
    
    # Create prompt template using imported prompts
    prompt = ChatPromptTemplate.from_messages([
        ("system", SCRIPT_WRITER_PROMPT),
        ("human", SCRIPT_WRITER_HUMAN_TEMPLATE)
    ])
    
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
        script_content = await chain.ainvoke({
            "template": state.slides,
            "slides_content": state.processed_summaries
        })
        
        # Write script to file
        output_path = Path(state.deck_info.path) / "audio" / "audio_script.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(script_content.content)
            
        # Update state
        state.audio_script = script_content.content
        
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