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
import shutil

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
            
        # Check if PDF exists in the correct directory
        deck_dir = state.get("deck_info", {}).get("path")
        if deck_dir:
            pdf_dir = Path(deck_dir) / "img" / "pdfs"
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if pdf_files:
                # Store PDF path in state
                state["pdf_path"] = str(pdf_files[0])
                return "process_imgs"
            else:
                # Check template directory for PDF
                template_dir = Path(deck_dir).parent / state["metadata"].template / "img" / "pdfs"
                template_pdfs = list(template_dir.glob("*.pdf"))
                if template_pdfs:
                    # Copy template PDF
                    pdf_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(template_pdfs[0], pdf_dir / template_pdfs[0].name)
                    state["pdf_path"] = str(pdf_dir / template_pdfs[0].name)
                    return "process_imgs"
        
        return "wait_for_pdf"
    
    # Add edges with conditions
    workflow.add_conditional_edges(
        "create_structure",
        should_process_pdf,
        ["process_imgs", "wait_for_pdf", END]
    )
    
    # Add conditional edge from extract_tables
    def should_process_summaries(state: BuilderState):
        """Determines if we should process summaries"""
        if state.get("error_context"):
            return END
        return "process_summaries"
    
    # Update edges for proper flow
    workflow.add_edge("process_imgs", "generate_summaries")
    workflow.add_edge("generate_summaries", "extract_tables")
    
    workflow.add_conditional_edges(
        "extract_tables",
        should_process_summaries,
        ["process_summaries", END]
    )
    
    # Add conditional edge from process_summaries
    def should_continue_processing(state: BuilderState):
        """Check if we should continue to slides"""
        if state.get("error_context"):
            return END
        if not state.get("processed_summaries"):
            return "process_summaries"
        return "process_slides"
    
    workflow.add_conditional_edges(
        "process_summaries",
        should_continue_processing,
        ["process_summaries", "process_slides", END]
    )
    
    workflow.add_edge("process_slides", "setup_audio")
    workflow.add_edge("setup_audio", END)
    workflow.add_edge("wait_for_pdf", END)
    
    # Set the entry point
    workflow.set_entry_point("create_structure")
    
    # Compile and return the graph
    return workflow.compile()

# Create an instance of the graph
builder_graph = create_builder_graph() 