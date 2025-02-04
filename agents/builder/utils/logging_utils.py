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
        
    # Only log minimal, non-sensitive information
    log_data = {
        "node": node_name,
        "change_type": change_type,
    }
    
    # Only include safe details that don't expose state
    if details:
        safe_keys = {'page_number', 'status', 'total_count'}
        safe_details = {k: v for k, v in details.items() if k in safe_keys}
        if safe_details:
            log_data.update(safe_details)
        
    logger.info(f"{node_name}: {change_type}")
    
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
    # Only log essential error information
    error_data = {
        "node": node_name,
        "error_type": type(error).__name__
    }
    
    # Include minimal context if provided
    if context:
        safe_keys = {'stage', 'step', 'status'}
        safe_context = {k: v for k, v in context.items() if k in safe_keys}
        if safe_context:
            error_data["context"] = safe_context
        
    logger.error(f"{node_name} failed: {type(error).__name__}")
    
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
    # Only log essential validation information
    status = "passed" if is_valid else "failed"
    
    # Include minimal details if provided
    if details:
        safe_keys = {'check_name', 'status'}
        safe_details = {k: v for k, v in details.items() if k in safe_keys}
        detail_str = f" - {safe_details}" if safe_details else ""
    else:
        detail_str = ""
        
    logger.info(f"Validation {status}: {validation_type}{detail_str}") 