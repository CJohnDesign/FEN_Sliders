"""Builder agent entry point."""
import os
import json
import asyncio
import logging
from pathlib import Path
from .graph import builder_graph
from .state import BuilderState
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

def convert_messages_to_dict(state):
    """Convert AIMessage objects to dictionaries for JSON serialization."""
    if isinstance(state, dict):
        return {k: convert_messages_to_dict(v) for k, v in state.items()}
    elif isinstance(state, list):
        return [convert_messages_to_dict(item) for item in state]
    elif isinstance(state, AIMessage):
        return {
            "type": "AIMessage",
            "content": state.content
        }
    return state

async def main():
    """Main entry point for the builder agent."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck-id", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    
    # Initialize state
    initial_state = {
        "messages": [],
        "metadata": {
            "deck_id": args.deck_id,
            "title": args.title,
            "template": "FEN_TEMPLATE",
            "theme_config": {}
        },
        "deck_info": None,
        "slides": [],
        "pdf_path": None,
        "pdf_info": None,
        "awaiting_input": None,
        "page_summaries": None,
        "processed_summaries": None,
        "error_context": None
    }
    
    logger.info(f"Starting builder for deck: {args.deck_id}")
    logger.info(f"Initial state: {initial_state}")
    
    try:
        final_state = await builder_graph.ainvoke(initial_state)
        
        # Save final state
        state_path = Path(f"decks/{args.deck_id}/state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(state_path, "w") as f:
            json.dump(convert_messages_to_dict(final_state), f, indent=2)
            
    except Exception as e:
        logger.error(f"Critical error in builder execution: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main()) 