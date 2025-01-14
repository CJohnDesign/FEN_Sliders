from ...utils import audio_utils
from ..state import BuilderState

async def setup_audio(state: BuilderState) -> BuilderState:
    """Sets up audio configuration and generates script"""
    try:
        # Skip if there was an error in previous steps
        if state.get("error_context"):
            return state
            
        # Set up audio script and config
        success = await audio_utils.setup_audio(
            state["metadata"].deck_id,
            state["metadata"].template,
            state["slides"]
        )
        
        if not success:
            state["error_context"] = {
                "error": "Failed to set up audio",
                "stage": "audio_setup"
            }
            return state
            
        state["audio_config"] = {
            "config_path": f"decks/{state['metadata'].deck_id}/audio/audio_config.json",
            "script_path": f"decks/{state['metadata'].deck_id}/audio/audio_script.md",
            "slide_count": len(state["slides"])
        }
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "audio_setup"
        }
        return state 