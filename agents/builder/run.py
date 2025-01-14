import argparse
import json
import asyncio
from typing import Dict, Any
import logging
import sys
from pathlib import Path

from .state import BuilderState, DeckMetadata
from .graph import builder_graph

TEMPLATE = "FEN_TEMPLATE"  # Only allowed template

# Set up logging
logging.basicConfig(
    filename='builder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add console handler for command line usage
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(message)s')  # Simplified format for console
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

def load_existing_deck_state(deck_id: str) -> Dict[str, Any]:
    """Load state from an existing deck"""
    base_dir = Path(__file__).parent.parent.parent
    deck_path = base_dir / "decks" / deck_id
    
    # Check if deck exists and has summaries
    if not deck_path.exists():
        return None
        
    summaries_path = deck_path / "ai" / "summaries.json"
    if not summaries_path.exists():
        return None
        
    try:
        with open(summaries_path) as f:
            summaries = json.load(f)
            
        return {
            "deck_info": {
                "path": str(deck_path),
                "template": TEMPLATE,
                "created": True
            },
            "page_summaries": summaries
        }
    except Exception as e:
        logging.error(f"Error loading existing deck state: {str(e)}")
        return None

async def run_builder(
    deck_id: str,
    title: str,
) -> Dict[str, Any]:
    """
    Run the deck builder workflow
    
    Args:
        deck_id: Unique identifier for the deck
        title: Title of the deck
        
    Returns:
        Dict containing the final state or error information
    """
    try:
        # Initialize base state with hardcoded logo path
        initial_state: BuilderState = {
            "messages": [],
            "metadata": DeckMetadata(
                deck_id=deck_id,
                title=title,
                template=TEMPLATE,
                theme_config={"logoHeader": "/logo.svg"}
            ),
            "slides": [],
            "audio_config": None,
            "error_context": None
        }
        
        # Check for existing deck state
        existing_state = load_existing_deck_state(deck_id)
        if existing_state:
            logging.info(f"Found existing deck {deck_id}, loading state")
            initial_state.update(existing_state)
        
        # Execute the graph
        final_state = await builder_graph.ainvoke(initial_state)
        
        logging.info("Build process completed")
        # Only log essential information, not the entire state
        logging.debug(f"Build completed for deck {deck_id} with {len(final_state.get('slides', []))} slides")
        
        result = {
            "status": "error" if final_state.get("error_context") else "success",
            "deck_id": deck_id,
            "error": final_state.get("error_context"),
            "slides_count": len(final_state.get("slides", [])),
            "audio_config": final_state.get("audio_config")
        }
        
        return result
        
    except Exception as e:
        logging.error(f"Unexpected error in build process: {str(e)}")
        return {
            "status": "error",
            "deck_id": deck_id,
            "error": {"error": str(e), "stage": "build_process"},
            "slides_count": 0,
            "audio_config": None
        }

def main():
    parser = argparse.ArgumentParser(description="Run the deck builder workflow")
    parser.add_argument("--deck-id", required=True, help="Unique identifier for the deck")
    parser.add_argument("--title", required=True, help="Title of the deck")
    
    args = parser.parse_args()
    
    try:
        # Run the workflow
        result = asyncio.run(run_builder(
            args.deck_id,
            args.title,
        ))
        
        # Log result summary without full data
        if result["status"] == "success":
            logging.info(f"Successfully built deck {args.deck_id} with {result['slides_count']} slides")
        else:
            logging.error(f"Failed to build deck {args.deck_id}: {result.get('error', 'Unknown error')}")
        
        # Output minimal JSON result to stdout
        minimal_result = {
            "status": result["status"],
            "deck_id": result["deck_id"],
            "slides_count": result["slides_count"]
        }
        if result["status"] == "error":
            minimal_result["error"] = str(result["error"])
            
        sys.stdout.write(json.dumps(minimal_result) + "\n")
        sys.exit(0 if result["status"] == "success" else 1)
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 