import argparse
import json
import asyncio
from typing import Dict, Any
import logging
import sys

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

async def run_builder(
    deck_id: str,
    title: str,
    theme_config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run the deck builder workflow
    
    Args:
        deck_id: Unique identifier for the deck
        title: Title of the deck
        theme_config: Optional theme configuration
        
    Returns:
        Dict containing the final state or error information
    """
    try:
        # Initialize state
        initial_state: BuilderState = {
            "messages": [],
            "metadata": DeckMetadata(
                deck_id=deck_id,
                title=title,
                template=TEMPLATE,
                theme_config=theme_config or {}
            ),
            "slides": [],
            "audio_config": None,
            "error_context": None
        }
        
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
    parser.add_argument("--theme-config", help="Theme configuration as JSON string")
    
    args = parser.parse_args()
    
    try:
        # Parse theme config if provided
        theme_config = json.loads(args.theme_config) if args.theme_config else None
        
        # Run the workflow
        result = asyncio.run(run_builder(
            args.deck_id,
            args.title,
            theme_config
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
        
    except json.JSONDecodeError:
        logging.error("Invalid theme configuration JSON")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 