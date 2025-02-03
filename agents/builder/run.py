"""Builder agent entry point."""
import os
import json
import asyncio
import logging
import argparse
from typing import Optional, Dict, Union
from pathlib import Path
from .graph import builder_graph
from .state import BuilderState, DeckMetadata, DeckInfo, convert_messages_to_dict
from langchain_core.messages import AIMessage
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
    "validate_sync",
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
        ),
        slides="",
        script="",
        slide_count=0,
        page_metadata=[],
        page_summaries=[],
        structured_slides=[],
        tables_data={},
        needs_fixes=False,
        retry_count=0,
        max_retries=3,
        validation_issues=[],
        error_context=None,
        messages=[]
    )

def load_existing_state(deck_id: str) -> Optional[BuilderState]:
    """Load existing state from state.json if it exists."""
    state_path = Path(f"decks/{deck_id}/state.json")
    if state_path.exists():
        logger.info(f"Loading existing state from {state_path}")
        with open(state_path) as f:
            state_dict = json.load(f)
            return BuilderState.model_validate(state_dict)
    return None

def save_state(state: Union[BuilderState, Dict], deck_id: str) -> None:
    """Save current state to disk."""
    try:
        state_path = Path(f"decks/{deck_id}/state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert state to dictionary format
        if isinstance(state, BuilderState):
            state_dict = state.model_dump(mode='json')
        elif isinstance(state, dict):
            # If it's a dict but contains Pydantic models, convert them
            state_dict = BuilderState.model_validate(state).model_dump(mode='json')
        else:
            raise ValueError(f"Unsupported state type: {type(state)}")
        
        # Write state to file
        with open(state_path, "w") as f:
            json.dump(state_dict, f, indent=2)
            
        logger.info(f"State saved to {state_path}")
        
    except Exception as e:
        logger.error(f"Error saving state: {str(e)}")
        logger.error(f"State type: {type(state)}")
        if isinstance(state, dict):
            logger.error("State keys: " + ", ".join(state.keys()))

def prepare_state_for_graph(state: BuilderState) -> Dict:
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
            state = load_existing_state(deck_id) or initialize_state(deck_id, title)
        else:
            state = initialize_state(deck_id, title)
        
        # Prepare state for graph execution
        graph_input = prepare_state_for_graph(state)
        
        # Add start node if specified
        if start_node:
            graph_input["start_node"] = start_node
        
        # Run workflow
        try:
            final_state = await builder_graph.ainvoke(graph_input)
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