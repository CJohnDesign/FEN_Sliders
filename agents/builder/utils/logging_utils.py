"""Standardized logging utilities for the builder agent."""
import logging
import functools
import traceback
from typing import Any, Callable, TypeVar, ParamSpec, Dict
from ..state import BuilderState

# Type variables for the decorator
P = ParamSpec('P')
T = TypeVar('T')

def setup_logger(name: str) -> logging.Logger:
    """Set up a standardized logger for the builder agent.
    
    Args:
        name: The name of the logger (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only add handlers if they don't exist
    if not logger.handlers:
        # Set up logging format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        file_handler = logging.FileHandler('builder.log')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
        # Set level
        logger.setLevel(logging.INFO)
    
    return logger

def log_async_step(logger: logging.Logger):
    """Decorator for logging async node execution steps with standardized error handling.
    
    Args:
        logger: The logger instance to use
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Get state from args (first argument should be state)
            state = args[0] if args else None
            
            # Check if state is a BuilderState
            if not isinstance(state, BuilderState):
                raise ValueError("First argument must be a BuilderState object")
            
            # Get function name without 'async' prefix
            func_name = func.__name__
            stage_name = func_name.replace('async_', '')
            
            try:
                # Log start
                logger.info(f"Starting {stage_name}...")
                logger.info(f"State contains: {[key for key in vars(state).keys()]}")
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Log completion if no errors
                if not result.error_context:
                    logger.info(f"Successfully completed {stage_name}")
                
                return result
                
            except Exception as e:
                # Get full traceback
                tb = traceback.format_exc()
                
                # Log error with full context
                logger.error(f"Critical error in {stage_name}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error message: {str(e)}")
                logger.error(f"Traceback:\n{tb}")
                
                # Update state with error context
                if isinstance(state, BuilderState):
                    state.error_context = {
                        "error": str(e),
                        "stage": stage_name,
                        "traceback": tb
                    }
                
                return state
                
        return wrapper
    return decorator

def log_step_result(logger: logging.Logger, stage: str, success: bool, message: str = None):
    """Log the result of a processing step with standardized format.
    
    Args:
        logger: The logger instance
        stage: The stage name
        success: Whether the step succeeded
        message: Optional message to include
    """
    status = "SUCCESS" if success else "FAILURE"
    msg = f"[{status}] {stage}"
    if message:
        msg += f": {message}"
        
    if success:
        logger.info(msg)
    else:
        logger.error(msg) 