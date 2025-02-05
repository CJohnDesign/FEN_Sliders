"""Builder workflow graph definition."""
from langgraph.graph import StateGraph
from langgraph.pregel import END
from typing import Annotated, TypeVar, Callable, Any
from .state import BuilderState, WorkflowStage
from .nodes import (
    create_deck,
    process_imgs,
    process_summaries,
    extract_tables,
    aggregate_summary,
    setup_slides,
    setup_script,
    validate,
    google_drive_sync
)

# Set up logging
import logging
logger = logging.getLogger(__name__)

def should_continue_validation(state: BuilderState) -> str:
    """Determine if validation should continue."""
    if not state.needs_fixes:
        logger.info("No fixes needed, proceeding to completion")
        return "complete"
    
    if state.retry_count >= state.max_retries:
        logger.warning(f"Hit max retries ({state.max_retries}), proceeding to completion")
        return "complete"
        
    logger.info(f"Content needs fixes (attempt {state.retry_count + 1}/{state.max_retries})")
    return "retry"

def create_builder_graph(start_node: str = "create_deck"):
    """Create the builder workflow graph.
    
    Args:
        start_node: The node to start the workflow from. Defaults to "create_deck".
    """
    # Initialize graph
    workflow = StateGraph(state_schema=BuilderState)
    
    # Add nodes - LangGraph will handle async/sync automatically
    workflow.add_node("create_deck", create_deck)
    workflow.add_node("process_imgs", process_imgs)
    workflow.add_node("process_summaries", process_summaries)
    workflow.add_node("extract_tables", extract_tables)
    workflow.add_node("aggregate_summary", aggregate_summary)
    workflow.add_node("setup_slides", setup_slides)
    workflow.add_node("setup_script", setup_script)
    workflow.add_node("validate", validate)
    workflow.add_node("google_drive_sync", google_drive_sync)
    
    # Set entry point based on start_node
    workflow.set_entry_point(start_node)
    
    # Define the main workflow edges
    edges = {
        "create_deck": "process_imgs",
        "process_imgs": "process_summaries",
        "process_summaries": "extract_tables",
        "extract_tables": "aggregate_summary",
        "aggregate_summary": "setup_slides",
        "setup_slides": "setup_script",
        "setup_script": "validate"
    }
    
    # Add edges based on start_node to ensure validation always happens
    if start_node == "validate":
        # If starting at validate, just add the validation loop
        pass
    else:
        # Find the starting point in the workflow
        current = start_node
        while current in edges:
            workflow.add_edge(current, edges[current])
            current = edges[current]
        # Always add edge to validation
        if current != "validate":
            workflow.add_edge(current, "validate")
    
    # Add validation loop
    workflow.add_conditional_edges(
        "validate",
        should_continue_validation,
        {
            "retry": "validate",  # Loop back for another validation attempt
            "complete": END  # Proceed to completion
        }
    )
    
    return workflow.compile()

# Don't create a global instance since we need the start_node parameter 