from typing import Any
from ...utils import deck_utils
from ..state import BuilderState

async def create_deck_structure(state: BuilderState) -> BuilderState:
    """Creates the basic deck structure based on template"""
    try:
        result = await deck_utils.create_structure(
            state["metadata"].deck_id,
            state["metadata"].template
        )
        
        if result["status"] == "error":
            state["error_context"] = {
                "error": result["error"],
                "stage": "deck_creation"
            }
        else:
            # Add success information to state
            state["deck_info"] = {
                "path": result["deck_path"],
                "template": result["template_used"]
            }
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "deck_creation"
        }
        return state 