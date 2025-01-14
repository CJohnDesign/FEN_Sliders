from langgraph.graph import StateGraph, END
from langchain.callbacks.manager import tracing_v2_enabled
from ..config.langsmith import init_langsmith, get_tracing_context
from ..utils.monitoring import DeckBuilderEvaluator, log_run_metrics
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
evaluator = DeckBuilderEvaluator()

def create_builder_graph():
    """Creates and returns a graph for processing PDFs and generating summaries"""
    
    # Initialize the graph with our state type
    workflow = StateGraph(BuilderState)
    
    # Add nodes with tracing
    async def create_structure(state):
        # Check if deck exists
        base_dir = Path(__file__).parent.parent.parent
        deck_path = base_dir / "decks" / state["metadata"].deck_id
        
        # Initialize deck_info first
        state["deck_info"] = {
            "path": str(deck_path),
            "template": state["metadata"].template,
            "created": not deck_path.exists()
        }
        
        if not state["deck_info"]["created"]:
            return state
            
        with get_tracing_context("deck-structure"):
            # Create deck structure
            deck_path.mkdir(parents=True, exist_ok=True)
            
            # Create required directories
            (deck_path / "img" / "pdfs").mkdir(parents=True, exist_ok=True)
            (deck_path / "ai").mkdir(parents=True, exist_ok=True)
            (deck_path / "audio").mkdir(parents=True, exist_ok=True)
            
            # Copy template files
            template_path = base_dir / "decks" / "FEN_TEMPLATE"
            
            # Copy PDFs
            template_pdfs = template_path / "img" / "pdfs"
            if template_pdfs.exists():
                deck_pdfs = deck_path / "img" / "pdfs"
                for pdf in template_pdfs.glob("*.pdf"):
                    import shutil
                    shutil.copy2(pdf, deck_pdfs / pdf.name)
                
            # Copy audio script template if exists
            template_audio = template_path / "audio" / "audio_script.md"
            if template_audio.exists():
                deck_audio = deck_path / "audio"
                shutil.copy2(template_audio, deck_audio / "audio_script.md")
            
            log_run_metrics(
                name="create_deck_structure",
                metrics={
                    "structure_created": True,
                    "deck_path": str(deck_path)
                }
            )
            return state
    
    async def process_images(state):
        # If deck existed before, skip image processing
        if "created" not in state.get("deck_info", {}):
            return state
            
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
    
    async def generate_summaries(state):
        # If deck existed before, skip summary generation
        if "created" not in state.get("deck_info", {}):
            # Load existing summaries if available
            deck_dir = state.get("deck_info", {}).get("path")
            if deck_dir:
                summaries_path = Path(deck_dir) / "ai" / "summaries.json"
                if summaries_path.exists():
                    with open(summaries_path) as f:
                        state["page_summaries"] = json.load(f)
            return state
            
        with get_tracing_context("summary-generation"):
            result = await generate_page_summaries(state)
            if result.get("page_summaries"):
                log_run_metrics(
                    name="generate_summaries",
                    metrics={
                        "summaries_generated": len(result["page_summaries"]),
                        "total_tokens": sum(s.get("token_count", 0) for s in result["page_summaries"])
                    }
                )
            return result

    async def extract_tables_node(state):
        with get_tracing_context("table-extraction"):
            return await extract_tables(state)

    async def process_summaries(state):
        with get_tracing_context("process-summaries"):
            # Ensure we have summaries
            if not state.get("page_summaries"):
                deck_dir = state.get("deck_info", {}).get("path")
                if deck_dir:
                    summaries_path = Path(deck_dir) / "ai" / "summaries.json"
                    if summaries_path.exists():
                        with open(summaries_path) as f:
                            state["page_summaries"] = json.load(f)
            return await process_summaries_node(state)
            
    async def process_slides(state):
        with get_tracing_context("slide-processing"):
            return await process_slides_node(state)
            
    async def setup_audio(state):
        with get_tracing_context("audio-setup"):
            return await setup_audio_node(state)
    
    workflow.add_node("create_structure", create_structure)
    workflow.add_node("wait_for_pdf", wait_for_pdf)
    workflow.add_node("process_imgs", process_images)
    workflow.add_node("generate_summaries", generate_summaries)
    workflow.add_node("extract_tables", extract_tables_node)
    workflow.add_node("process_summaries", process_summaries)
    workflow.add_node("process_slides", process_slides)
    workflow.add_node("setup_audio", setup_audio)
    
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
        # List all possible destinations
        ["process_imgs", "wait_for_pdf", "process_summaries", END]
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
    
    # Define the conditional edge function for table extraction
    def should_extract_tables(state: BuilderState):
        """Determines if we should extract tables"""
        if state.get("error_context"):
            return END
            
        # Check if summaries.json exists
        deck_dir = state.get("deck_info", {}).get("path")
        if deck_dir:
            summaries_path = Path(deck_dir) / "ai" / "summaries.json"
            if summaries_path.exists():
                return "extract_tables"
            
        return "process_summaries"

    # Add edges with conditions
    workflow.add_conditional_edges(
        "generate_summaries",
        should_extract_tables,
        ["extract_tables", "process_summaries", END]
    )
    
    # Update other edges
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