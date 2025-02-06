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
    # Check if we have validation issues
    if not state.validation_issues:
        logger.info("No validation issues found, proceeding to completion")
        return "complete"
        
    # Check if we're in a failed state
    if (state.error_context and 
        state.error_context.stage == WorkflowStage.VALIDATE):
        logger.warning("Validation failed, proceeding to completion")
        return "complete"
        
    # Check current stage progress
    if state.workflow_progress.stages.get(WorkflowStage.VALIDATE):
        validate_progress = state.workflow_progress.stages[WorkflowStage.VALIDATE]
        if validate_progress.status == "failed":
            logger.warning("Validation stage failed, proceeding to completion")
            return "complete"
            
    logger.info("Content needs fixes, retrying validation")
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
    
    # Define the main workflow edges with stage transitions
    edges = {
        # INIT -> EXTRACT
        "create_deck": "process_imgs",
        
        # EXTRACT -> PROCESS
        "process_imgs": "process_summaries",
        
        # PROCESS stage steps
        "process_summaries": "extract_tables",
        "extract_tables": "aggregate_summary",
        
        # PROCESS -> GENERATE
        "aggregate_summary": "setup_slides",
        
        # GENERATE stage steps
        "setup_slides": "setup_script",
        
        # GENERATE -> VALIDATE
        "setup_script": "validate"
    }
    
    # Set entry point based on start_node
    if start_node not in edges and start_node != "validate":
        logger.error(f"Invalid start node: {start_node}")
        start_node = "create_deck"
    workflow.set_entry_point(start_node)
    
    # Add edges based on start_node
    current = start_node
    while current in edges:
        workflow.add_edge(current, edges[current])
        current = edges[current]
        
    # Always ensure we end with validation
    if current != "validate" and current in edges:
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