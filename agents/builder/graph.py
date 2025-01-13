from langgraph.graph import StateGraph, END
from langchain.callbacks.manager import tracing_v2_enabled
from ..config.langsmith import init_langsmith, get_tracing_context
from ..utils.monitoring import DeckBuilderEvaluator, log_run_metrics
from .state import BuilderState
from .nodes import create_deck_structure, wait_for_pdf, process_imgs, generate_page_summaries
from pathlib import Path

# Initialize LangSmith
client = init_langsmith()
evaluator = DeckBuilderEvaluator()

def create_builder_graph():
    """Creates and returns a graph for processing PDFs and generating summaries"""
    
    # Initialize the graph with our state type
    workflow = StateGraph(BuilderState)
    
    # Add nodes with tracing
    async def traced_create_structure(state):
        with get_tracing_context("deck-structure"):
            result = await create_deck_structure(state)
            log_run_metrics(
                name="create_deck_structure",
                metrics={
                    "structure_created": True,
                    "deck_path": str(state.get("deck_info", {}).get("path", ""))
                }
            )
            return result
    
    async def traced_process_imgs(state):
        with get_tracing_context("image-processing"):
            result = await process_imgs(state)
            if result.get("pdf_info"):
                log_run_metrics(
                    name="process_images",
                    metrics={
                        "pages_processed": result["pdf_info"].get("page_count", 0),
                        "pdf_path": str(result["pdf_info"].get("path", ""))
                    }
                )
            return result
    
    async def traced_generate_summaries(state):
        with get_tracing_context("summary-generation"):
            result = await generate_page_summaries(state)
            if result.get("summaries"):
                log_run_metrics(
                    name="generate_summaries",
                    metrics={
                        "summaries_generated": len(result["summaries"]),
                        "total_tokens": sum(s.get("token_count", 0) for s in result["summaries"])
                    }
                )
            return result
    
    workflow.add_node("create_structure", traced_create_structure)
    workflow.add_node("wait_for_pdf", wait_for_pdf)
    workflow.add_node("process_imgs", traced_process_imgs)
    workflow.add_node("generate_summaries", traced_generate_summaries)
    
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