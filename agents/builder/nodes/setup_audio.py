"""Audio setup node for preparing presentation audio."""
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, WorkflowStage
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..prompts.script_writer_prompts import (
    SCRIPT_WRITER_SYSTEM_PROMPT,
    SCRIPT_WRITER_HUMAN_PROMPT
)

# Set up logging
logger = logging.getLogger(__name__)

def get_template(template_path: Path) -> str:
    """Get the audio script template from the template folder."""
    try:
        template_file = template_path / "audio" / "audio_script.md"
        if not template_file.exists():
            logger.error(f"Template file not found: {template_file}")
            return ""
            
        with open(template_file) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading template: {str(e)}")
        return ""

async def setup_audio(state: BuilderState) -> BuilderState:
    """Set up audio script for the presentation."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.SETUP_AUDIO:
            logger.warning(f"Expected stage {WorkflowStage.SETUP_AUDIO}, but got {state.current_stage}")
            
        # Check for slides content
        if not state.slides:
            logger.warning("No slides content found in state")
            state.error_context = {
                "error": "No slides content available",
                "stage": "audio_setup"
            }
            return state
            
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", SCRIPT_WRITER_SYSTEM_PROMPT),
            ("human", SCRIPT_WRITER_HUMAN_PROMPT)
        ])
        
        # Create and execute the chain
        llm = await get_llm(temperature=0.2)
        chain = prompt | llm
        
        # Generate audio script
        logger.info("Generating audio script...")
        response = await chain.ainvoke({
            "template": state.audio_script if hasattr(state, 'audio_script') else "",  # Handle case where audio_script doesn't exist
            "slides_content": state.slides
        })
        audio_script = response.content
        
        # Write audio script to file
        # Get the deck path from state.deck_info.path
        if not hasattr(state, 'deck_info') or not hasattr(state.deck_info, 'path'):
            logger.error("Missing deck_info.path in state")
            state.error_context = {
                "error": "Missing deck path information",
                "stage": "audio_setup"
            }
            return state
            
        output_path = Path(state.deck_info.path) / "audio" / "audio_script.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(audio_script)
            
        # Update state with generated content
        state.audio_script = audio_script
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="setup_audio",
            change_type="complete",
            details={"output_path": str(output_path)}
        )
        
        # Update workflow stage
        state.current_stage = WorkflowStage.VALIDATE
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "setup_audio", e)
        state.error_context = {
            "error": str(e),
            "stage": "audio_setup"
        }
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 