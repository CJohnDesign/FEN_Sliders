"""Retry utilities for the builder."""
import asyncio
import functools
import logging
from typing import TypeVar, Callable, Any

T = TypeVar("T")

def retry_with_exponential_backoff(
    max_retries: int = 3,
    min_seconds: float = 4,
    max_seconds: float = 10,
    factor: float = 2,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a function with exponential backoff."""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_try = 1
            current_delay = min_seconds
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if current_try > max_retries:
                        raise
                        
                    sleep_time = min(max_seconds, current_delay * (factor ** (current_try - 1)))
                    logging.warning(
                        f"Error in {func.__name__}, attempt {current_try} of {max_retries}. "
                        f"Retrying in {sleep_time} seconds... Error: {str(e)}"
                    )
                    
                    asyncio.sleep(sleep_time)
                    current_try += 1
                    
        return wrapper
    return decorator 