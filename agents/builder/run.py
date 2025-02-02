"""Builder agent entry point."""
import os
import json
import asyncio
import logging
import argparse
from pathlib import Path
from .graph import builder_graph
from .state import BuilderState, DeckMetadata, convert_messages_to_dict
from langchain_core.messages import AIMessage
from ..config.settings import LANGCHAIN_TRACING_V2, LANGCHAIN_PROJECT

# Set up LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

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

def load_existing_state(deck_id: str) -> BuilderState:
    """Load existing state from state.json if it exists."""
    state_path = Path(f"decks/{deck_id}/state.json")
    if state_path.exists():
        logger.info(f"Loading existing state from {state_path}")
        with open(state_path) as f:
            state_dict = json.load(f)
            # Convert dictionary to BuilderState
            metadata = DeckMetadata(**state_dict.get('metadata', {}))
            return BuilderState(
                messages=state_dict.get('messages', []),
                metadata=metadata,
                deck_info=state_dict.get('deck_info', {}),
                slides=state_dict.get('slides', []),
                script=state_dict.get('script'),
                pdf_path=state_dict.get('pdf_path'),
                pdf_info=state_dict.get('pdf_info'),
                awaiting_input=state_dict.get('awaiting_input'),
                page_summaries=state_dict.get('page_summaries'),
                processed_summaries=state_dict.get('processed_summaries'),
                audio_config=state_dict.get('audio_config'),
                error_context=state_dict.get('error_context'),
                needs_fixes=state_dict.get('needs_fixes', False),
                retry_count=state_dict.get('retry_count', 0),
                validation_issues=state_dict.get('validation_issues', [])
            )
    return None

async def run_builder(deck_id: str, title: str, start_node: str = None) -> int:
    """Run the builder workflow.
    
    Args:
        deck_id: ID for the deck
        title: Title for the deck
        start_node: Optional node to start from. Must be one of VALID_NODES.
    """
    logger.info(f"Starting builder for deck: {deck_id}")
    
    if start_node and start_node not in VALID_NODES:
        logger.error(f"Invalid start node: {start_node}. Must be one of: {', '.join(VALID_NODES)}")
        return 1
    
    # Initialize state
    if start_node:
        # Load existing state when starting from a specific node
        existing_state = load_existing_state(deck_id)
        if existing_state:
            logger.info("Using existing state")
            initial_state = existing_state
        else:
            logger.warning("No existing state found, starting fresh")
            initial_state = BuilderState(
                messages=[],
                metadata=DeckMetadata(deck_id=deck_id, title=title),
                deck_info={"path": f"decks/{deck_id}", "template": "FEN_TEMPLATE"}
            )
    else:
        initial_state = BuilderState(
            messages=[],
            metadata=DeckMetadata(deck_id=deck_id, title=title),
            deck_info={"path": f"decks/{deck_id}", "template": "FEN_TEMPLATE"}
        )
    
    logger.info(f"Initial state: {initial_state}")
    
    try:
        # Run workflow using ainvoke for async execution
        if start_node:
            logger.info(f"Starting workflow from node: {start_node}")
            final_state = await builder_graph.ainvoke(initial_state, {"start_node": start_node})
        else:
            final_state = await builder_graph.ainvoke(initial_state)
        
        # Convert final state to dictionary for safe access
        if not isinstance(final_state, dict):
            final_state = dict(final_state)
        
        # Check for errors using dictionary access
        if final_state.get('error_context'):
            logger.error("Builder workflow failed")
            logger.error(f"Error context: {final_state['error_context']}")
            return 1
            
        # Convert to serializable dictionary
        final_dict = convert_messages_to_dict(final_state)
            
        # Write final state
        state_path = Path(f"decks/{deck_id}/state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(final_dict, f, indent=2)
            
        logger.info("Builder completed successfully")
        return 0
            
    except Exception as e:
        logger.error(f"Critical error in builder execution: {str(e)}")
        logger.error("Full error context:", exc_info=True)
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