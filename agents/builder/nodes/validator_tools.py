"""Tools available to the validator node."""
import logging
from typing import Dict, Any, Tuple
from ..state import BuilderState
from .slides_writer import slides_writer
from .script_writer import script_writer

logger = logging.getLogger(__name__)

async def fix_slides(state: BuilderState) -> Tuple[BuilderState, Dict[str, Any]]:
    """Tool to fix slide issues."""
    try:
        logger.info("Invoking slides_writer tool")
        if not state.validation_issues or not state.validation_issues.slide_issues:
            logger.info("No slide issues to fix")
            return state, {
                "success": True,
                "changes_made": False,
                "message": "No slide issues to fix"
            }
            
        # Store original slides for comparison
        original_slides = state.slides if hasattr(state, 'slides') else None
        
        if not original_slides:
            logger.warning("No slides content to fix")
            return state, {
                "success": False,
                "changes_made": False,
                "message": "No slides content available to fix"
            }
            
        # Pass validation issues and suggested fixes to slides writer
        state.validation_issues.suggested_fixes = state.validation_issues.suggested_fixes if hasattr(state.validation_issues, 'suggested_fixes') else {}
        
        # Call slides writer
        updated_state = await slides_writer(state)
        
        # Check if changes were made
        changes_made = (
            updated_state.slides != original_slides
            if original_slides is not None and hasattr(updated_state, 'slides')
            else False
        )
        
        if not changes_made:
            logger.warning("Slides writer made no changes")
            
        return updated_state, {
            "success": True,
            "changes_made": changes_made,
            "message": "Slides updated successfully" if changes_made else "No changes needed in slides"
        }
    except Exception as e:
        logger.error(f"Error in slides_writer tool: {str(e)}")
        return state, {
            "success": False,
            "changes_made": False,
            "message": f"Failed to update slides: {str(e)}"
        }

async def fix_script(state: BuilderState) -> Tuple[BuilderState, Dict[str, Any]]:
    """Tool to fix script issues."""
    try:
        logger.info("Invoking script_writer tool")
        if not state.validation_issues or not state.validation_issues.script_issues:
            logger.info("No script issues to fix")
            return state, {
                "success": True,
                "changes_made": False,
                "message": "No script issues to fix"
            }
            
        # Store original script for comparison
        original_script = state.script if hasattr(state, 'script') else None
        
        if not original_script:
            logger.warning("No script content to fix")
            return state, {
                "success": False,
                "changes_made": False,
                "message": "No script content available to fix"
            }
            
        # Pass validation issues and suggested fixes to script writer
        state.validation_issues.suggested_fixes = state.validation_issues.suggested_fixes if hasattr(state.validation_issues, 'suggested_fixes') else {}
        
        # Call script writer
        updated_state = await script_writer(state)
        
        # Check if changes were made
        changes_made = (
            updated_state.script != original_script
            if original_script is not None and hasattr(updated_state, 'script')
            else False
        )
        
        if not changes_made:
            logger.warning("Script writer made no changes")
            
        return updated_state, {
            "success": True,
            "changes_made": changes_made,
            "message": "Script updated successfully" if changes_made else "No changes needed in script"
        }
    except Exception as e:
        logger.error(f"Error in script_writer tool: {str(e)}")
        return state, {
            "success": False,
            "changes_made": False,
            "message": f"Failed to update script: {str(e)}"
        }

VALIDATOR_TOOLS = {
    "fix_slides": fix_slides,
    "fix_script": fix_script
} 