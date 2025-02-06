"""State utilities for the builder agent."""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from ..state import BuilderState, ValidationIssues, ValidationIssue, DeckMetadata, WorkflowStage

# Set up logging
logger = logging.getLogger(__name__)

def migrate_old_state(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate old state format to new format."""
    logger.info("Migrating old state format to new format...")
    
    # Force legacy stage to lowercase for proper mapping
    old_stage = state_dict.get("current_stage", "init")
    if isinstance(old_stage, str):
        old_stage = old_stage.lower()
    new_stage = WorkflowStage.map_legacy_stage(old_stage)
    logger.info(f"Mapping stage from {old_stage} to {new_stage}")
    
    # Create new state dict with only allowed fields
    new_state = {
        "slides": state_dict.get("slides"),
        "script": state_dict.get("script"),
        "needs_fixes": state_dict.get("needs_fixes", False),
        "retry_count": state_dict.get("retry_count", 0),
        "max_retries": state_dict.get("max_retries", 3),
        "current_stage": new_stage
    }
    
    # Handle metadata migration
    if "metadata" in state_dict:
        old_metadata = state_dict["metadata"]
        if isinstance(old_metadata, dict):
            new_metadata = {
                "deck_id": old_metadata.get("deck_id"),
                "title": old_metadata.get("title"),
                "description": old_metadata.get("description"),
                "author": old_metadata.get("author", "FirstEnroll"),
                "created_at": old_metadata.get("created_at"),
                "updated_at": old_metadata.get("updated_at")
            }
            # Only include non-None values
            new_state["metadata"] = {k: v for k, v in new_metadata.items() if v is not None}
    
    # Handle validation issues migration
    if "validation_issues" in state_dict:
        old_issues = state_dict["validation_issues"]
        new_issues = {
            "script_issues": [],
            "slide_issues": []
        }
        
        # Convert old format to new format
        if isinstance(old_issues, list):
            new_issues["script_issues"] = [
                {
                    "section": issue.get("section", "unknown"),
                    "issue": issue.get("issue", "unknown"),
                    "severity": issue.get("severity", "medium"),
                    "suggestions": issue.get("suggestions", [])
                }
                for issue in old_issues
            ]
        elif isinstance(old_issues, dict):
            new_issues["script_issues"] = [
                {
                    "section": issue.get("section", "unknown"),
                    "issue": issue.get("issue", "unknown"),
                    "severity": issue.get("severity", "medium"),
                    "suggestions": issue.get("suggestions", [])
                }
                for issue in old_issues.get("script_issues", [])
            ]
            new_issues["slide_issues"] = [
                {
                    "section": issue.get("section", "unknown"),
                    "issue": issue.get("issue", "unknown"),
                    "severity": issue.get("severity", "medium"),
                    "suggestions": issue.get("suggestions", [])
                }
                for issue in old_issues.get("slide_issues", [])
            ]
        
        new_state["validation_issues"] = new_issues
    
    # Handle error context migration
    if "error_context" in state_dict:
        old_error = state_dict["error_context"]
        if isinstance(old_error, dict):
            error_stage = old_error.get("stage", "unknown")
            if isinstance(error_stage, str):
                error_stage = error_stage.lower()
            new_state["error_context"] = {
                "error": old_error.get("error", "Unknown error"),
                "stage": WorkflowStage.map_legacy_stage(error_stage),
                "details": old_error.get("details", {})
            }
    
    logger.debug(f"Migrated state keys: {list(new_state.keys())}")
    return new_state

def load_existing_state(deck_id: str) -> Optional[BuilderState]:
    """Load existing state from disk if available."""
    try:
        state_path = Path(f"decks/{deck_id}/state.json")
        if not state_path.exists():
            logger.info(f"No existing state found at {state_path}")
            return None
            
        logger.info(f"Loading existing state from {state_path}")
        
        # Check if file is empty
        if state_path.stat().st_size == 0:
            logger.warning(f"State file is empty: {state_path}")
            return None
            
        try:
            with open(state_path, 'r') as f:
                state_dict = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse state file: {str(e)}")
            return None
            
        if not isinstance(state_dict, dict):
            logger.error(f"Invalid state format: expected dict, got {type(state_dict)}")
            return None
            
        try:
            # Create BuilderState directly from dict
            state = BuilderState.model_validate(state_dict)
            logger.info(f"Successfully loaded state with stage: {state.workflow_progress.current_stage}")
            return state
        except Exception as e:
            logger.error(f"Failed to create BuilderState: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"Failed to load state: {str(e)}")
        return None

async def save_state(state: Union[BuilderState, Dict[str, Any]], deck_id: str) -> BuilderState:
    """Save current state to disk and return the state."""
    try:
        # Ensure deck directory exists
        state_dir = Path(f"decks/{deck_id}")
        state_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert state to BuilderState if it's a dict
        if isinstance(state, dict):
            builder_state = BuilderState.model_validate(state)
        else:
            builder_state = state
            
        # Save to file
        state_path = state_dir / "state.json"
        state_dict = builder_state.to_dict()
        with open(state_path, 'w') as f:
            json.dump(state_dict, f, indent=2)
            
        logger.info(f"State saved to {state_path}")
        return builder_state
        
    except Exception as e:
        logger.error(f"Failed to save state: {str(e)}")
        logger.error(f"State type: {type(state)}")
        if not isinstance(state, BuilderState):
            logger.error(f"State keys: {list(state.keys()) if hasattr(state, 'keys') else 'no keys'}")
        raise

def prepare_state_for_graph(state: BuilderState) -> dict:
    """Prepare state for graph execution."""
    # Convert state to dict excluding config and model_config
    state_dict = state.model_dump(
        exclude={'config', 'model_config'},
        mode='json'
    )
    return state_dict 