"""Builder workflow graph definition."""
from langgraph.graph import StateGraph
from langgraph.pregel import END
from .state import BuilderState
from .nodes import (
    create_deck_structure,
    process_imgs,
    process_summaries,
    extract_tables,
    aggregate_summary,
    process_slides,
    setup_audio,
    validate_and_fix,
    google_drive_sync
)

def create_builder_graph(start_node: str = "create_deck"):
    """Create the builder workflow graph.
    
    Args:
        start_node: The node to start the workflow from. Defaults to "create_deck".
    """
    # Initialize graph
    workflow = StateGraph(state_schema=BuilderState)
    
    # Add nodes - LangGraph will handle async/sync automatically
    workflow.add_node("create_deck", create_deck_structure)
    workflow.add_node("process_imgs", process_imgs)
    workflow.add_node("process_summaries", process_summaries)
    workflow.add_node("extract_tables", extract_tables)
    workflow.add_node("aggregate_summary", aggregate_summary)
    workflow.add_node("process_slides", process_slides)
    workflow.add_node("setup_audio", setup_audio)
    workflow.add_node("validate", validate_and_fix)
    workflow.add_node("google_drive_sync", google_drive_sync)
    
    # Set entry point based on start_node
    workflow.set_entry_point(start_node)
    
    # Define simple linear flow
    workflow.add_edge("create_deck", "process_imgs")
    workflow.add_edge("process_imgs", "process_summaries")
    workflow.add_edge("process_summaries", "extract_tables")
    workflow.add_edge("extract_tables", "aggregate_summary")
    workflow.add_edge("aggregate_summary", "process_slides")
    workflow.add_edge("process_slides", "setup_audio")
    workflow.add_edge("setup_audio", "validate")
    workflow.add_edge("validate", "google_drive_sync")
    workflow.add_edge("google_drive_sync", END)
    
    return workflow.compile()

# Don't create a global instance since we need the start_node parameter 