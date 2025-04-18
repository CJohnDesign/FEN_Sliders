"""Builder agent entry point."""
import os
import asyncio
import logging
import argparse
from typing import Optional
from pathlib import Path
from .graph import create_builder_graph
from .state import BuilderState, DeckMetadata, DeckInfo, WorkflowStage, WorkflowProgress, StageProgress
from .utils.state_utils import load_existing_state, save_state
from ..config.settings import LANGCHAIN_TRACING_V2, LANGCHAIN_PROJECT
from datetime import datetime

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
VALID_START_NODES = [
    "create_deck",
    "process_imgs",
    "process_summaries",
    "extract_tables",
    "aggregate_summary",
    "setup_slides",
    "setup_script",
    "validate",
    "google_drive_sync",
]

# Map node names to workflow stages
STAGE_MAPPING = {
    "create_deck": WorkflowStage.INIT,
    "process_imgs": WorkflowStage.EXTRACT,
    "process_summaries": WorkflowStage.PROCESS,
    "extract_tables": WorkflowStage.PROCESS,
    "aggregate_summary": WorkflowStage.PROCESS,
    "setup_slides": WorkflowStage.GENERATE,
    "setup_script": WorkflowStage.GENERATE,
    "validate": WorkflowStage.VALIDATE,
    "google_drive_sync": WorkflowStage.EXPORT
}

def initialize_state(deck_id: str, title: str) -> BuilderState:
    """Initialize a fresh state with default values."""
    if not deck_id or not isinstance(deck_id, str):
        raise ValueError("deck_id must be a non-empty string")
    if not title or not isinstance(title, str):
        raise ValueError("title must be a non-empty string")
        
    state = BuilderState(
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
        ),
        workflow_progress=WorkflowProgress(
            current_stage=WorkflowStage.INIT,
            stages={
                WorkflowStage.INIT: StageProgress(
                    status="in_progress",
                    started_at=datetime.now().isoformat()
                )
            }
        )
    )
    
    logger.info(f"Initialized state with stage: {state.workflow_progress.current_stage}")
    return state

def prepare_state_for_graph(state: BuilderState) -> dict:
    """Prepare state for graph execution."""
    # Convert state to dictionary format, excluding config
    state_dict = state.model_dump(
        mode='json',
        exclude={'config'}
    )
    return state_dict

async def run_builder(deck_id: str, title: str, start_node: str = None) -> int:
    """Run the builder workflow."""
    try:
        # Validate inputs
        if not deck_id or not isinstance(deck_id, str):
            logger.error("Invalid deck_id provided")
            return 1
        if not title or not isinstance(title, str):
            logger.error("Invalid title provided")
            return 1
            
        # Initialize or load state
        state = None
        if start_node:
            # Try to load existing state
            state = load_existing_state(deck_id)
            logger.info(f"Attempting to load existing state for {deck_id}")
            
        # Create new state if none exists
        if not state:
            state = initialize_state(deck_id, title)
            logger.info(f"Created new state for deck {deck_id}")
            
        # Set the current stage based on start_node
        if start_node:
            try:
                if start_node not in STAGE_MAPPING:
                    logger.error(f"Invalid start node: {start_node}")
                    return 1
                    
                stage = STAGE_MAPPING[start_node]
                state.update_stage(stage)
                logger.info(f"Set current stage to: {stage}")
                
            except ValueError as e:
                logger.error(f"Error setting workflow stage: {str(e)}")
                return 1
        
        # Prepare state for graph execution
        graph_input = prepare_state_for_graph(state)
        
        # Create graph with specified start node
        graph = create_builder_graph(start_node or "create_deck")
        logger.info(f"Created graph starting from node: {start_node or 'create_deck'}")
        
        # Run workflow
        try:
            final_state = await graph.ainvoke(graph_input)
            await save_state(final_state, deck_id)
            logger.info("Builder completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Graph execution failed: {str(e)}")
            await save_state(state, deck_id)
            return 1
            
    except Exception as e:
        logger.error(f"Builder initialization failed: {str(e)}")
        return 1

def main():
    """Parse arguments and run the builder."""
    parser = argparse.ArgumentParser(description="Run the deck builder")
    parser.add_argument("--deck-id", required=True, help="ID for the deck")
    parser.add_argument("--title", required=True, help="Title for the deck")
    parser.add_argument("--start-node", choices=VALID_START_NODES, help="Node to start from")
    args = parser.parse_args()
    
    return asyncio.run(run_builder(args.deck_id, args.title, args.start_node))

if __name__ == "__main__":
    exit(main()) 