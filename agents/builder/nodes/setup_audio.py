"""Audio setup node for preparing presentation audio."""
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

def create_audio_chain():
    """Create the chain for generating audio script."""
    # Use centralized LLM configuration
    llm = get_llm(temperature=0.2)
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_template(
        """Convert the following script into a natural, conversational audio script.
        The audio script should:
        1. Flow naturally between sections
        2. Use clear pronunciation guides for technical terms
        3. Include appropriate pauses and emphasis
        4. Maintain professional but approachable tone
        5. Include timing markers for synchronization
        
        Script Content:
        {content}
        
        Format the audio script to be clear and well-structured."""
    )
    
    # Create chain
    chain = prompt | llm
    
    return chain

async def setup_audio(state: BuilderState) -> BuilderState:
    """Set up audio script for the presentation."""
    try:
        # Check for script content
        if not state.script:
            logger.warning("No script content found in state")
            state.error_context = {
                "error": "No script content available",
                "stage": "audio_setup"
            }
            return state
            
        # Create audio chain
        chain = create_audio_chain()
        
        # Generate audio script
        audio_script = await chain.ainvoke({"content": state.script})
        
        # Write audio script to file
        output_path = Path(state.deck_info.path) / "audio" / "audio_script.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(audio_script)
            
        # Update state
        state.audio_script = audio_script
        
        # Log completion
        log_state_change(
            state=state,
            node_name="setup_audio",
            change_type="complete",
            details={"output_path": str(output_path)}
        )
        
        return state
        
    except Exception as e:
        log_error(state, "setup_audio", e)
        state.error_context = {
            "error": str(e),
            "stage": "audio_setup"
        }
        return state 