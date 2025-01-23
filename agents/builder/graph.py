"""Builder workflow graph definition."""
import os
from langgraph.graph import StateGraph
from .state import BuilderState
from .nodes import (
    create_deck_structure,
    process_slides,
    process_imgs,
    generate_page_summaries,
    extract_tables,
    process_summaries,
    setup_audio
)
from .nodes.summary import process_plan_tiers

def create_builder_graph() -> StateGraph:
    """Create the builder workflow graph."""
    # Initialize graph
    workflow = StateGraph(BuilderState)
    
    # Add nodes
    workflow.add_node("create_deck", create_deck_structure)
    workflow.add_node("process_imgs", process_imgs)
    workflow.add_node("generate_summaries", generate_page_summaries)
    workflow.add_node("extract_tables", extract_tables)
    workflow.add_node("process_plan_tiers", process_plan_tiers)
    workflow.add_node("process_summaries", process_summaries)
    workflow.add_node("process_slides", process_slides)
    workflow.add_node("setup_audio", setup_audio)
    
    # Add edges
    workflow.add_edge("create_deck", "process_imgs")
    workflow.add_edge("process_imgs", "generate_summaries")
    workflow.add_edge("generate_summaries", "extract_tables")
    workflow.add_edge("extract_tables", "process_plan_tiers")
    workflow.add_edge("process_plan_tiers", "process_summaries")
    workflow.add_edge("process_summaries", "process_slides")
    workflow.add_edge("process_slides", "setup_audio")
    
    # Set entry point
    workflow.set_entry_point("create_deck")
    
    return workflow.compile()

# Create graph instance
builder_graph = create_builder_graph() 