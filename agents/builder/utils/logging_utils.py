"""Logging utilities for the builder agent."""
import logging
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel
from ..state import BuilderState

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def log_state_change(
    state: BuilderState,
    node_name: str,
    change_type: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log state changes in a standardized format.
    
    Args:
        state: Current BuilderState
        node_name: Name of the node making the change
        change_type: Type of change (e.g., 'update', 'error', 'complete')
        details: Optional dictionary of additional details to log
    """
    if not isinstance(state, BuilderState):
        raise ValueError("First argument must be a BuilderState object")
        
    log_data = {
        "node": node_name,
        "change_type": change_type,
        "deck_id": state.metadata.deck_id if state.metadata else None,
        "state": state.model_dump(exclude={'messages'}) if isinstance(state, BaseModel) else state,
    }
    
    if details:
        log_data.update(details)
        
    logger.info(f"State Change: {log_data}")
    
def log_error(
    state: Union[BuilderState, Dict[str, Any]], 
    node_name: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Log errors in a standardized format.
    
    Args:
        state: Current BuilderState or state dict
        node_name: Name of the node where error occurred
        error: The exception that was raised
        context: Optional dictionary of additional context
    """
    error_data = {
        "node": node_name,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "deck_id": None
    }
    
    # Extract deck_id safely
    if isinstance(state, BuilderState):
        error_data["deck_id"] = state.metadata.deck_id if state.metadata else None
        error_data["state"] = state.model_dump(exclude={'messages'})
    elif isinstance(state, dict):
        metadata = state.get('metadata', {})
        error_data["deck_id"] = metadata.get('deck_id') if metadata else None
        error_data["state"] = state
        
    if context:
        error_data["context"] = context
        
    logger.error(f"Error in builder: {error_data}", exc_info=True)
    
def log_validation(
    state: BuilderState,
    validation_type: str,
    is_valid: bool,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log validation results in a standardized format.
    
    Args:
        state: Current BuilderState
        validation_type: Type of validation performed
        is_valid: Whether validation passed
        details: Optional dictionary of validation details
    """
    validation_data = {
        "validation_type": validation_type,
        "is_valid": is_valid,
        "deck_id": state.metadata.deck_id if state.metadata else None
    }
    
    if details:
        validation_data["details"] = details
        
    if is_valid:
        logger.info(f"Validation passed: {validation_data}")
    else:
        logger.warning(f"Validation failed: {validation_data}") 