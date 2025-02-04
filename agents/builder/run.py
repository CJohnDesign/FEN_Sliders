"""Builder agent entry point."""
import os
import asyncio
import logging
import argparse
from typing import Optional
from pathlib import Path
from .graph import create_builder_graph
from .state import BuilderState, DeckMetadata, DeckInfo, WorkflowStage
from .utils.state_utils import load_existing_state, save_state
from ..config.settings import LANGCHAIN_TRACING_V2, LANGCHAIN_PROJECT

# Set up LangSmith configuration
os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_VERBOSE"] = "true"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Valid starting nodes in the graph
VALID_NODES = [
    "create_deck",
    "process_imgs",
    "process_summaries",
    "extract_tables",
    "process_slides",
    "setup_audio",
    "validate",
    "slides_writer",
    "script_writer"
]

def initialize_state(deck_id: str, title: str) -> BuilderState:
    """Initialize a fresh state with default values."""
    return BuilderState(
        metadata=DeckMetadata(
            deck_id=deck_id,
            title=title,
            version="1.0.0",
            author="FirstEnroll",
            theme="default"
        ),
        deck_info=DeckInfo(
            path=f"decks/{deck_id}",
            template="FEN_TEMPLATE"
        )
    )

def prepare_state_for_graph(state: BuilderState) -> dict:
    """Prepare state for graph execution."""
    # Convert state to dictionary format
    state_dict = state.model_dump(mode='json')
    
    # Add any required runtime configuration
    state_dict["config"] = {
        "allow_delegation": True,
        "max_iterations": 10
    }
    
    return state_dict

async def run_builder(deck_id: str, title: str, start_node: str = None) -> int:
    """Run the builder workflow."""
    try:
        # Initialize or load state
        if start_node:
            # Load existing state or create new one
            state = load_existing_state(deck_id)
            if not state:
                state = initialize_state(deck_id, title)
                logger.info(f"Created new state for deck {deck_id}")
            else:
                logger.info(f"Loaded existing state for deck {deck_id}")
            
            # Set the current stage based on start_node
            try:
                # Convert node name to workflow stage
                stage_map = {
                    "create_deck": WorkflowStage.CREATE_DECK,
                    "process_imgs": WorkflowStage.PROCESS_IMAGES,
                    "process_summaries": WorkflowStage.PROCESS_SUMMARIES,
                    "extract_tables": WorkflowStage.EXTRACT_TABLES,
                    "aggregate_summary": WorkflowStage.AGGREGATE_SUMMARY,
                    "process_slides": WorkflowStage.PROCESS_SLIDES,
                    "setup_audio": WorkflowStage.SETUP_AUDIO,
                    "validate": WorkflowStage.VALIDATE,
                    "google_drive_sync": WorkflowStage.GOOGLE_DRIVE_SYNC
                }
                
                if start_node not in stage_map:
                    logger.error(f"Invalid start node: {start_node}")
                    return 1
                    
                stage = stage_map[start_node]
                state.current_stage = stage
                logger.info(f"Set current stage to: {stage}")
                
                # Remove this stage and all subsequent stages from completed_stages
                if hasattr(state, 'completed_stages') and state.completed_stages:
                    stage_order = list(WorkflowStage)
                    start_idx = stage_order.index(stage)
                    stages_to_remove = set(stage_order[start_idx:])
                    state.completed_stages = [s for s in state.completed_stages if s not in stages_to_remove]
                    logger.info(f"Reset completed stages after {stage}")
            except ValueError as e:
                logger.error(f"Error setting workflow stage: {str(e)}")
                return 1
        else:
            state = initialize_state(deck_id, title)
            start_node = "create_deck"  # Default start node
            logger.info("Starting fresh workflow from create_deck")
        
        # Prepare state for graph execution
        graph_input = prepare_state_for_graph(state)
        
        # Create graph with specified start node
        graph = create_builder_graph(start_node)
        logger.info(f"Created graph starting from node: {start_node}")
        
        # Run workflow
        try:
            final_state = await graph.ainvoke(graph_input)
            save_state(final_state, deck_id)
            logger.info("Builder completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Graph execution failed: {str(e)}")
            save_state(state, deck_id)
            return 1
            
    except Exception as e:
        logger.error(f"Builder initialization failed: {str(e)}")
        return 1

def main():
    """Parse arguments and run the builder."""
    parser = argparse.ArgumentParser(description="Run the deck builder")
    parser.add_argument("--deck-id", required=True, help="ID for the deck")
    parser.add_argument("--title", required=True, help="Title for the deck")
    parser.add_argument("--start-node", choices=VALID_NODES, help="Node to start from")
    args = parser.parse_args()
    
    return asyncio.run(run_builder(args.deck_id, args.title, args.start_node))

if __name__ == "__main__":
    exit(main()) 