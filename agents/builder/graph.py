from langgraph.graph import StateGraph, END
from .state import BuilderState
from .nodes import create_deck_structure, wait_for_pdf, process_imgs, generate_page_summaries
from pathlib import Path

def create_builder_graph():
    """Creates and returns a graph for processing PDFs and generating summaries"""
    
    # Initialize the graph with our state type
    workflow = StateGraph(BuilderState)
    
    # Add nodes
    workflow.add_node("create_structure", create_deck_structure)
    workflow.add_node("wait_for_pdf", wait_for_pdf)
    workflow.add_node("process_imgs", process_imgs)
    workflow.add_node("generate_summaries", generate_page_summaries)
    
    # Define the conditional edge function for PDF processing
    def should_process_pdf(state: BuilderState):
        """Determines if we should process PDF or wait"""
        if state.get("error_context"):
            return END
            
        # Check if PDF exists in the correct directory
        deck_dir = state.get("deck_info", {}).get("path")
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
        # List all possible destinations
        ["process_imgs", "wait_for_pdf", END]
    )
    
    # Define the conditional edge function for summary generation
    def should_generate_summaries(state: BuilderState):
        """Determines if we should generate summaries"""
        if state.get("error_context"):
            return END
            
        if state.get("pdf_info", {}).get("page_count", 0) > 0:
            return "generate_summaries"
            
        return END
    
    # Add edges for image processing and summary generation
    workflow.add_conditional_edges(
        "process_imgs",
        should_generate_summaries,
        ["generate_summaries", END]
    )
    workflow.add_edge("generate_summaries", END)
    workflow.add_edge("wait_for_pdf", END)
    
    # Set the entry point
    workflow.set_entry_point("create_structure")
    
    # Compile and return the graph
    return workflow.compile()

# Create an instance of the graph
builder_graph = create_builder_graph() 