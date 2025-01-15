import argparse
import asyncio
import logging
from pathlib import Path
import json
import os

from .graph import builder_graph
from .state import BuilderState, DeckMetadata

# Set up LangSmith project
os.environ["LANGCHAIN_PROJECT"] = "fen-deck-builder"

logging.basicConfig(
    filename='builder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def main():
    parser = argparse.ArgumentParser(description='Run the deck builder')
    parser.add_argument('--deck-id', required=True, help='ID of the deck to build')
    parser.add_argument('--title', required=True, help='Title of the deck')
    parser.add_argument('--template', default='FEN_TEMPLATE', help='Template to use')
    args = parser.parse_args()
    
    # Initialize state
    state = BuilderState(
        messages=[],
        metadata=DeckMetadata(
            deck_id=args.deck_id,
            title=args.title,
            template=args.template,
            theme_config={}
        ),
        slides=[],
        audio_config=None,
        error_context=None,
        deck_info=None,
        awaiting_input=None,
        pdf_path=None,
        pdf_info=None,
        pdf_analysis=None,
        page_summaries=None
    )
    
    # Run the graph
    try:
        final_state = await builder_graph.ainvoke(state)
        
        # Save final state
        deck_path = Path("decks") / args.deck_id
        state_file = deck_path / "state.json"
        
        # Convert state to serializable format
        def convert_to_serializable(obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            elif hasattr(obj, "content"):  # Handle AIMessage
                return obj.content
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            return obj
            
        serializable_state = {
            "metadata": convert_to_serializable(final_state["metadata"]),
            "messages": convert_to_serializable(final_state["messages"]),
            "slides": convert_to_serializable(final_state.get("slides", [])),
            "audio_config": convert_to_serializable(final_state.get("audio_config")),
            "error_context": convert_to_serializable(final_state.get("error_context")),
            "deck_info": convert_to_serializable(final_state.get("deck_info")),
            "awaiting_input": convert_to_serializable(final_state.get("awaiting_input")),
            "pdf_path": convert_to_serializable(final_state.get("pdf_path")),
            "pdf_info": convert_to_serializable(final_state.get("pdf_info")),
            "pdf_analysis": convert_to_serializable(final_state.get("pdf_analysis")),
            "page_summaries": convert_to_serializable(final_state.get("page_summaries"))
        }
        
        with open(state_file, "w") as f:
            json.dump(serializable_state, f, indent=2)
            
        # Log final state summary
        logging.info("\nFinal state summary:")
        logging.info(f"Status: {'Error' if final_state.get('error_context') else 'Success'}")
        logging.info(f"Slides count: {len(final_state.get('slides', []))}")
        if final_state.get('error_context'):
            logging.error(f"Error: {final_state.get('error_context')}")
            
    except Exception as e:
        logging.error(f"Failed to run builder: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 