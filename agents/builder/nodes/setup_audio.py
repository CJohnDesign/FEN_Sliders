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
            
        # Get template path
        base_dir = Path(__file__).parent.parent.parent.parent
        template_dir = base_dir / "decks" / state.deck_info.template
        
        # Create system and human messages
        system_message = SystemMessage(content="""You are an expert at creating presentation scripts.
            
Guidelines for script content:
- Keep the tone professional but conversational
- Each section should be marked with ---- Section Title ----
- Each v-click point should have its own paragraph
- Maintain natural transitions between sections
- Include clear verbal cues for slide transitions
- Do not wrap the content in ```markdown or ``` tags""")

        # Use audio script from state if available, otherwise use template
        script_content = state.audio_script if state.audio_script else get_template(template_dir)
        if not script_content:
            logger.error("No audio script template available")
            state.error_context = {
                "error": "No audio script template available",
                "stage": "audio_setup"
            }
            return state
        
        human_message = HumanMessage(content=f"""

Use this script structure as your base - the headers have ---- on either side of them - eg ---- Section Title ----. keep this format.
{script_content}

Generate a script using this complete slides content:
{state.slides}

---

Update the content while maintaining the exact formatting from the script.
Do not wrap the content in ```markdown or ``` tags.

Important:
- headers have ---- on either side of them, ie ---- Section Title ----. keep this format.
- Create a script that follows the slides exactly
- Each slide's content should be clearly marked
- Include verbal cues for transitions and animations (v-clicks)
- Maintain professional but engaging tone
- Script should be natural and conversational""")
        
        # Create and execute the chain
        prompt = ChatPromptTemplate.from_messages([system_message, human_message])
        llm = await get_llm(temperature=0.2)
        chain = prompt | llm
        
        # Generate audio script
        logger.info("Generating audio script...")
        response = await chain.ainvoke({})
        audio_script = response.content
        
        # Write audio script to file
        output_path = Path(state.deck_info.path) / "audio" / "audio_script.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(audio_script)
            
        # Update state
        state.audio_script = audio_script
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="setup_audio",
            change_type="complete",
            details={"output_path": str(output_path)}
        )
        
        # Update workflow stage
        state.update_stage(WorkflowStage.SETUP_AUDIO)
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