from ...utils import audio_utils
from ..state import BuilderState

async def setup_audio(state: BuilderState) -> BuilderState:
    """Sets up audio configuration and generates script"""
    try:
        # Skip if there was an error in previous steps
        if state.get("error_context"):
            return state
            
        # Generate audio config
        config_result = await audio_utils.generate_audio_config(
            state["metadata"].deck_id,
            state["metadata"].template
        )
        
        if config_result["status"] == "error":
            state["error_context"] = {
                "error": config_result["error"],
                "stage": "audio_config"
            }
            return state
            
        # Process audio script
        script_result = await audio_utils.process_audio_script(
            state["metadata"].deck_id,
            state["slides"]
        )
        
        if not script_result:
            state["error_context"] = {
                "error": "Failed to generate audio script",
                "stage": "audio_script"
            }
            return state
            
        state["audio_config"] = {
            "config_path": config_result["config_path"],
            "script_path": script_result["script_path"],
            "slide_count": script_result["slide_count"]
        }
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "audio_setup"
        }
        return state 