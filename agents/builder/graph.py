from langgraph.graph import StateGraph, END
from ..config.langsmith import init_langsmith
from .state import BuilderState
from .nodes import (
    create_deck_structure, 
    wait_for_pdf, 
    process_imgs, 
    generate_page_summaries,
    extract_tables,
    process_summaries as process_summaries_node, 
    process_slides as process_slides_node, 
    setup_audio as setup_audio_node
)
from pathlib import Path
import json

# Initialize LangSmith
client = init_langsmith()

def create_builder_graph():
    """Create the builder workflow graph"""
    workflow = StateGraph(BuilderState)
    
    # Add nodes (no manual tracing needed - LangGraph handles this)
    workflow.add_node("create_structure", create_deck_structure)
    workflow.add_node("wait_for_pdf", wait_for_pdf)
    workflow.add_node("process_imgs", process_imgs)
    workflow.add_node("generate_summaries", generate_page_summaries)
    workflow.add_node("extract_tables", extract_tables)
    workflow.add_node("process_summaries", process_summaries_node)
    workflow.add_node("process_slides", process_slides_node)
    workflow.add_node("setup_audio", setup_audio_node)
    
    # Define the conditional edge function for PDF processing
    def should_process_pdf(state: BuilderState):
        """Determines if we should process PDF or wait"""
        if state.get("error_context"):
            return END
            
        # Check if summaries.json exists
        deck_dir = state.get("deck_info", {}).get("path")
        if deck_dir:
            summaries_path = Path(deck_dir) / "ai" / "summaries.json"
            if summaries_path.exists():
                # Load existing summaries into state
                with open(summaries_path) as f:
                    state["page_summaries"] = json.load(f)
                return "process_summaries"
                
        # Check if PDF exists in the correct directory
        if deck_dir:
            pdf_dir = Path(deck_dir) / "img" / "pdfs"
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if pdf_files:
                return "process_imgs"
        
        return "wait_for_pdf"
    
    # Add edges with conditions
    workflow.add_conditional_edges(
        "create_structure",
        should_process_pdf,
        ["process_imgs", "wait_for_pdf", "process_summaries", END]
    )
    
    # Update other edges
    workflow.add_edge("process_imgs", "generate_summaries")
    workflow.add_edge("generate_summaries", "extract_tables")
    workflow.add_edge("extract_tables", "process_summaries")
    workflow.add_edge("process_summaries", "process_slides")
    workflow.add_edge("process_slides", "setup_audio")
    workflow.add_edge("setup_audio", END)
    workflow.add_edge("wait_for_pdf", END)
    
    # Set the entry point
    workflow.set_entry_point("create_structure")
    
    # Compile and return the graph
    return workflow.compile()

# Create an instance of the graph
builder_graph = create_builder_graph() 