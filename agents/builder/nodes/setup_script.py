"""Setup audio node for generating and saving audio script."""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from ..state import BuilderState, WorkflowStage, WorkflowProgress, StageProgress
from ..utils.state_utils import save_state
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_completion
from langchain.prompts import ChatPromptTemplate
from langsmith.run_helpers import traceable
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

async def save_audio_script(state: BuilderState, audio_script: str) -> bool:
    """Save audio script to file.
    
    Args:
        state: Current builder state
        audio_script: Generated audio script content
        
    Returns:
        bool indicating success
    """
    try:
        if not state.deck_info or not state.deck_info.path:
            logger.error("Missing deck info or path")
            return False
            
        # Create audio directory
        audio_path = Path(state.deck_info.path) / "audio"
        audio_path.mkdir(parents=True, exist_ok=True)
        
        # Save script
        script_path = audio_path / "audio_script.md"
        script_path.write_text(audio_script)
        logger.info(f"Saved audio script to {script_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving audio script: {str(e)}")
        return False

async def generate_audio_script(state: BuilderState) -> Optional[str]:
    """Generate audio script from slides content.
    
    Args:
        state: Current builder state
        
    Returns:
        Generated audio script or None if error
    """
    try:
        if not state.slides_content:
            logger.error("No slides content found")
            return None
            
        # Create messages for completion
        messages = [
            {"role": "system", "content": "You are an expert at creating natural, engaging audio scripts from slide content."},
            {"role": "human", "content": f"Generate an audio script for the following slides:\n\n{state.slides_content}"}
        ]
        
        # Generate script using get_completion
        audio_script = await get_completion(messages, temperature=0.7)
        return audio_script
        
    except Exception as e:
        logger.error(f"Error generating audio script: {str(e)}")
        return None

@traceable(name="setup_script")
async def setup_script(state: BuilderState) -> BuilderState:
    """Set up script based on processed content."""
    try:
        logger.info("Starting script setup")
        
        # Initialize workflow progress if not present
        if not state.workflow_progress:
            state.workflow_progress = WorkflowProgress(
                current_stage=WorkflowStage.GENERATE,
                stages={
                    WorkflowStage.GENERATE: StageProgress(
                        status="in_progress",
                        started_at=datetime.now().isoformat()
                    )
                }
            )
        
        # Verify we're in the correct stage
        if state.workflow_progress.current_stage != WorkflowStage.GENERATE:
            logger.warning(f"Expected stage {WorkflowStage.GENERATE}, got {state.workflow_progress.current_stage}")
            state.update_stage(WorkflowStage.GENERATE)
            
        # Check for slides content
        if not state.slides_content:
            error_msg = "No slides content found"
            logger.error(error_msg)
            state.set_error(error_msg, "setup_script")
            return state
            
        # Generate audio script
        audio_script = await generate_audio_script(state)
        if not audio_script:
            error_msg = "Failed to generate audio script"
            logger.error(error_msg)
            state.set_error(error_msg, "setup_script")
            return state
            
        # Save audio script
        if not await save_audio_script(state, audio_script):
            error_msg = "Failed to save audio script"
            logger.error(error_msg)
            state.set_error(error_msg, "setup_script")
            return state
            
        # Update state
        state.script_content = audio_script
        
        # Log completion
        log_state_change(
            state=state,
            node_name="setup_script",
            change_type="complete",
            details={
                "script_content_length": len(audio_script)
            }
        )
        
        # Move to validation stage
        state.update_stage(WorkflowStage.VALIDATE)
        
        # Save state
        await save_state(state, state.metadata.deck_id)
        
        return state
        
    except Exception as e:
        error_msg = f"Error in setup_script: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "setup_script")
        return state 