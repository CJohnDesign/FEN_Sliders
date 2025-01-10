import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from .graph import builder_graph
from .state import BuilderState, DeckMetadata

# Set up logging
logging.basicConfig(
    filename='builder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add console handler for test output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(message)s')
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

async def run_test(
    deck_id: str,
    step: Optional[str] = None,
    load_state: bool = False
) -> None:
    """Run the test workflow"""
    try:
        # Get deck path
        deck_path = str(Path(__file__).parent.parent.parent / "decks" / f"FEN_{deck_id}")
        logging.info(f"Using deck path: {deck_path}")
        
        # Initialize state
        state: BuilderState
        
        logging.info("Initializing state...")
        
        if load_state:
            logging.info("Loading saved state...")
            state_file = Path(deck_path) / "state.json"
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
            else:
                raise ValueError("No saved state found")
        else:
            logging.info("Creating new state...")
            state = {
                "messages": [],
                "metadata": DeckMetadata(
                    deck_id=deck_id,
                    title=f"Test Deck {deck_id}",
                    template="FEN_TEMPLATE",
                    theme_config={}
                ),
                "slides": [],
                "audio_config": None,
                "error_context": None,
                "deck_info": {
                    "path": deck_path,
                    "template": "FEN_TEMPLATE"
                }
            }
            
        # Run specific step or full workflow
        if step:
            logging.info(f"Running step: {step}")
            if hasattr(builder_graph, step):
                node = getattr(builder_graph, step)
                final_state = await node(state)
            else:
                logging.error(f"Unknown step: {step}")
                return
        else:
            final_state = await builder_graph.ainvoke(state)
            
        # Save final state
        state_file = Path(deck_path) / "state.json"
        with open(state_file, "w") as f:
            json.dump(final_state, f, indent=2)
            
        # Log final state summary
        logging.info("\nFinal state summary:")
        logging.info(f"Status: {'Error' if final_state.get('error_context') else 'Success'}")
        logging.info(f"Slides count: {len(final_state.get('slides', []))}")
        if final_state.get("error_context"):
            logging.error(f"Error: {final_state['error_context']}")
            
        # Log messages without full content
        if final_state.get("messages"):
            logging.info("\nMessage count: {len(final_state['messages'])}")
            for message in final_state["messages"]:
                if hasattr(message, "content"):
                    # Only log first 100 chars of message content
                    content = message.content[:100] + "..." if len(message.content) > 100 else message.content
                    logging.info(f"AI message: {content}")
                    
    except asyncio.TimeoutError:
        logging.error("Timeout: The operation took too long to complete")
    except Exception as e:
        logging.error(f"Error running step: {str(e)}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("deck_id", help="Deck ID to test")
    parser.add_argument("--step", help="Specific step to run")
    parser.add_argument("--load-state", action="store_true", help="Load existing state")
    
    args = parser.parse_args()
    
    asyncio.run(run_test(args.deck_id, args.step, args.load_state))

if __name__ == "__main__":
    main() 