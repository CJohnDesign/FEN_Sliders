"""Builder workflow graph definition."""
import os
from langgraph.graph import StateGraph
from .state import BuilderState
from .nodes import (
    create_deck_structure,
    generate_slides,
    process_pdf,
    process_audio,
    generate_summaries,
    extract_tables,
    process_summaries
)

def create_builder_graph() -> StateGraph:
    """Create the builder workflow graph."""
    # Initialize graph
    workflow = StateGraph(BuilderState)
    
    # Add nodes
    workflow.add_node("create_deck", create_deck_structure)
    workflow.add_node("process_pdf", process_pdf)
    workflow.add_node("generate_summaries", generate_summaries)
    workflow.add_node("extract_tables", extract_tables)
    workflow.add_node("process_summaries", process_summaries)
    workflow.add_node("generate_slides", generate_slides)
    workflow.add_node("process_audio", process_audio)
    
    # Add edges
    workflow.add_edge("create_deck", "process_pdf")
    workflow.add_edge("process_pdf", "generate_summaries")
    workflow.add_edge("generate_summaries", "extract_tables")
    workflow.add_edge("extract_tables", "process_summaries")
    workflow.add_edge("process_summaries", "generate_slides")
    workflow.add_edge("generate_slides", "process_audio")
    
    # Set entry point
    workflow.set_entry_point("create_deck")
    
    return workflow.compile()

# Create graph instance
builder_graph = create_builder_graph() 