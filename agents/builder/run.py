"""Builder agent entry point."""
import os
import json
import asyncio
import argparse
from pathlib import Path
from .graph import builder_graph
from .state import DeckMetadata
from .utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger(__name__)

async def main():
    """Run the builder agent."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run the builder agent")
    parser.add_argument("--deck-id", required=True, help="ID for the deck")
    parser.add_argument("--title", required=True, help="Title for the deck")
    args = parser.parse_args()
    
    # Create decks directory if it doesn't exist
    Path("decks").mkdir(exist_ok=True)
    
    # Initialize state with required fields
    state = {
        "messages": [],  # Required for LangGraph
        "metadata": DeckMetadata(
            deck_id=args.deck_id,
            title=args.title,
            template="FEN_TEMPLATE",
            theme_config={}
        ).dict(),
        "deck_info": None,
        "slides": [],
        "pdf_path": None,
        "pdf_info": None,
        "awaiting_input": None,
        "page_summaries": None,
        "processed_summaries": None,
        "audio_config": None,
        "error_context": None
    }
    
    logger.info(f"Starting builder for deck: {args.deck_id}")
    logger.info(f"Initial state: {state}")
    
    try:
        # Run builder graph
        final_state = await builder_graph.ainvoke(state)
        
        # Save final state
        state_path = Path(f"decks/{args.deck_id}/state.json")
        state_path.parent.mkdir(exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(final_state, f, indent=2)
        logger.info(f"Final state saved to {state_path}")
            
    except Exception as e:
        logger.error(f"Critical error in builder execution: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main()) 