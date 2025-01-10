from ...utils import slide_utils
from ..state import BuilderState

async def process_slides(state: BuilderState) -> BuilderState:
    """Processes and validates slides"""
    try:
        # Skip if there was an error in previous steps
        if state.get("error_context"):
            return state
            
        slides = await slide_utils.process_slides(
            state["metadata"].deck_id,
            state["metadata"].template
        )
        
        # Validate slides
        is_valid = await slide_utils.validate_slide_structure(
            slides,
            state["metadata"].template
        )
        
        if not is_valid:
            state["error_context"] = {
                "error": "Invalid slide structure",
                "stage": "slide_validation"
            }
            return state
            
        state["slides"] = slides
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "slide_processing"
        }
        return state 