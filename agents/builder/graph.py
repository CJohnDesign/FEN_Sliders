"""Builder workflow graph definition."""
from langgraph.graph import StateGraph
from langgraph.pregel import END
from .state import BuilderState
from .nodes import (
    create_deck_structure,
    process_imgs,
    process_summaries,
    extract_tables,
    process_slides,
    setup_audio,
    validate_and_fix
)

def create_builder_graph():
    """Create the builder workflow graph."""
    # Initialize graph
    workflow = StateGraph(state_schema=BuilderState)
    
    # Add nodes - LangGraph will handle async/sync automatically
    workflow.add_node("create_deck", create_deck_structure)
    workflow.add_node("process_imgs", process_imgs)
    workflow.add_node("process_summaries", process_summaries)
    workflow.add_node("extract_tables", extract_tables)
    workflow.add_node("process_slides", process_slides)
    workflow.add_node("setup_audio", setup_audio)
    workflow.add_node("validate", validate_and_fix)
    
    # Set entry point
    workflow.set_entry_point("create_deck")
    
    # Define simple linear flow
    workflow.add_edge("create_deck", "process_imgs")
    workflow.add_edge("process_imgs", "process_summaries")
    workflow.add_edge("process_summaries", "extract_tables")
    workflow.add_edge("extract_tables", "process_slides")
    workflow.add_edge("process_slides", "setup_audio")
    workflow.add_edge("setup_audio", "validate")
    workflow.add_edge("validate", END)
    
    return workflow.compile()

# Create graph instance
builder_graph = create_builder_graph() 