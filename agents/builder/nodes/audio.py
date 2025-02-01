"""Audio generation node for the builder agent."""
from ...utils import audio_utils
from ..state import BuilderState

async def setup_audio(state: BuilderState) -> BuilderState:
    """Sets up audio script generation"""
    try:
        # Skip if there was an error in previous steps
        if state.get("error_context"):
            return state
            
        # Check for processed summaries
        if not state.get("processed_summaries"):
            state["error_context"] = {
                "error": "No processed summaries available",
                "stage": "audio_setup"
            }
            return state
            
        # Set up audio script
        success = await audio_utils.setup_audio(
            state["metadata"]["deck_id"],
            state["metadata"]["template"],
            [],  # Empty slides list since we're using processed summaries
            state["processed_summaries"]
        )
        
        if not success:
            state["error_context"] = {
                "error": "Failed to set up audio script",
                "stage": "audio_setup"
            }
            return state
            
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "audio_setup"
        }
        return state 