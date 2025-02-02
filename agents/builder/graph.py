"""Builder workflow graph definition."""
import os
import logging
from typing import Annotated, Dict, TypeVar, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.pregel import END
from .state import BuilderState
from .nodes import (
    create_deck_structure,
    process_slides,
    process_imgs,
    process_summaries,
    extract_tables,
    setup_audio,
    validate_and_fix,
    slides_writer,
    script_writer
)

# Set up logging
logger = logging.getLogger(__name__)

# Type for state
State = TypeVar("State", bound=BuilderState)

def create_builder_graph() -> StateGraph:
    """Create the builder workflow graph."""
    # Initialize graph
    workflow = StateGraph(BuilderState)
    
    # Add nodes
    workflow.add_node("create_deck", create_deck_structure)
    workflow.add_node("process_imgs", process_imgs)
    workflow.add_node("process_summaries", process_summaries)
    workflow.add_node("extract_tables", extract_tables)
    workflow.add_node("process_slides", process_slides)
    workflow.add_node("setup_audio", setup_audio)
    workflow.add_node("validate_sync", validate_and_fix)
    workflow.add_node("slides_writer", slides_writer)
    workflow.add_node("script_writer", script_writer)
    
    # Add edges for main flow
    workflow.add_edge("create_deck", "process_imgs")
    workflow.add_edge("process_imgs", "extract_tables")
    workflow.add_edge("extract_tables", "process_summaries")
    workflow.add_edge("process_summaries", "process_slides")
    workflow.add_edge("process_slides", "setup_audio")
    workflow.add_edge("setup_audio", "validate_sync")
    
    # Define conditional branching for validation loop
    def validation_router(state: State) -> Literal["continue", "end"]:
        """Route to next node or end based on validation state."""
        if state.retry_count >= 5:
            logger.info(f"Max retries ({state.retry_count}) reached. Ending workflow.")
            return "end"
        if not state.needs_fixes:
            logger.info("No fixes needed. Ending workflow.")
            return "end"
        logger.info(f"Continuing with retry {state.retry_count + 1}")
        return "continue"
    
    # Add validation loop edges with conditional routing
    workflow.add_conditional_edges(
        "validate_sync",
        validation_router,
        {
            "continue": "slides_writer",
            "end": END
        }
    )

    # Add sequential writer edges
    workflow.add_edge("slides_writer", "script_writer")
    workflow.add_edge("script_writer", "validate_sync")
    
    # Set entry point
    workflow.set_entry_point("create_deck")
    
    return workflow.compile()

# Create graph instance
builder_graph = create_builder_graph() 