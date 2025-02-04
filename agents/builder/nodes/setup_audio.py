"""Audio setup node for preparing presentation audio."""
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, WorkflowStage
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ...utils.content import save_content
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

async def save_audio_files(state: BuilderState, audio_script: str, audio_config: Dict[str, Any]) -> Tuple[bool, bool]:
    """Save audio script and config files."""
    try:
        if not state.deck_info or not state.deck_info.path:
            logger.error("Missing deck_info.path in state")
            return False, False
            
        deck_path = Path(state.deck_info.path)
        audio_path = deck_path / "audio"
        audio_path.mkdir(parents=True, exist_ok=True)
        
        # Save audio script
        script_path = audio_path / "audio_script.md"
        script_saved = False
        try:
            await save_content(script_path, audio_script)
            logger.info(f"Saved audio script to {script_path}")
            script_saved = True
        except Exception as e:
            logger.error(f"Failed to save audio script: {str(e)}")
            
        # Save audio config
        config_path = audio_path / "audio_config.json"
        config_saved = False
        try:
            with open(config_path, "w") as f:
                json.dump(audio_config, f, indent=2)
            logger.info(f"Saved audio config to {config_path}")
            config_saved = True
        except Exception as e:
            logger.error(f"Failed to save audio config: {str(e)}")
            
        return script_saved, config_saved
            
    except Exception as e:
        logger.error(f"Error saving audio files: {str(e)}")
        return False, False

def generate_audio_config(state: BuilderState) -> Dict[str, Any]:
    """Generate audio configuration from state."""
    try:
        if not state.structured_slides:
            logger.warning("No structured slides found in state")
            return {
                "version": "1.0",
                "slides": []
            }
            
        return {
            "version": "1.0",
            "deckId": state.metadata.deck_id if state.metadata else "",
            "totalSlides": len(state.structured_slides),
            "slides": [
                {
                    "slideNumber": slide.page_number,
                    "clicks": []
                }
                for slide in state.structured_slides
            ]
        }
    except Exception as e:
        logger.error(f"Error generating audio config: {str(e)}")
        return {
            "version": "1.0",
            "slides": []
        }

async def setup_audio(state: BuilderState) -> BuilderState:
    """Set up audio script for the presentation."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.SETUP_AUDIO:
            logger.warning(f"Expected stage {WorkflowStage.SETUP_AUDIO}, but got {state.current_stage}")
            if state.current_stage == WorkflowStage.PROCESS_SLIDES:
                logger.error("Cannot proceed - previous stage (PROCESS_SLIDES) did not complete successfully")
                state.set_error(
                    "Process slides stage did not complete successfully",
                    "audio_setup",
                    {"previous_stage": "PROCESS_SLIDES"}
                )
                return state
            state.update_stage(WorkflowStage.SETUP_AUDIO)
            
        # Validate required state attributes
        required_attrs = {
            "slides": "Slides content",
            "structured_slides": "Structured slides",
            "deck_info": "Deck information",
            "metadata": "Deck metadata",
            "processed_summaries": "Processed summaries"
        }
        
        for attr, desc in required_attrs.items():
            if not hasattr(state, attr) or not getattr(state, attr):
                logger.error(f"Missing required state attribute: {attr}")
                state.set_error(
                    f"Missing {desc}",
                    "audio_setup",
                    {"missing": [attr]}
                )
                return state

        # Get template from deck info
        template_path = Path(state.deck_info.path).parent / state.deck_info.template
        template = get_template(template_path)
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", SCRIPT_WRITER_SYSTEM_PROMPT),
            ("human", SCRIPT_WRITER_HUMAN_PROMPT.format(
                template=template,
                slides_content=state.slides,
                processed_summaries=state.processed_summaries
            ))
        ])
        
        # Create and execute the chain
        llm = await get_llm(temperature=0.2)
        chain = prompt | llm
        
        # Generate audio script
        logger.info("Generating audio script...")
        response = await chain.ainvoke({})
        audio_script = response.content
        
        # Validate audio script
        if not audio_script or not audio_script.strip():
            logger.error("Generated audio script is empty")
            state.set_error(
                "Generated audio script is empty",
                "audio_setup"
            )
            return state
            
        # Generate audio config
        audio_config = generate_audio_config(state)
        if not audio_config["slides"]:
            logger.error("Generated audio config has no slides")
            state.set_error(
                "Failed to generate valid audio configuration",
                "audio_setup"
            )
            return state
            
        # Save files
        script_saved, config_saved = await save_audio_files(state, audio_script, audio_config)
        if not script_saved or not config_saved:
            state.set_error(
                "Failed to save audio files",
                "audio_setup",
                {
                    "script_saved": script_saved,
                    "config_saved": config_saved
                }
            )
            return state
            
        # Update state with generated content
        state.audio_script = audio_script
        state.audio_config = audio_config
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="setup_audio",
            change_type="complete",
            details={
                "script_saved": script_saved,
                "config_saved": config_saved,
                "total_slides": len(audio_config["slides"])
            }
        )
        
        # Save state before transitioning
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        # Update workflow stage
        state.update_stage(WorkflowStage.VALIDATE)
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state again after stage transition
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            
        return state
        
    except Exception as e:
        log_error(state, "setup_audio", e)
        state.set_error(
            str(e),
            "audio_setup"
        )
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 