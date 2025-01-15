"""Slide generation node for the builder agent."""
import os
import json
import logging
from pathlib import Path
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..utils.retry_utils import retry_with_exponential_backoff
from ..utils.logging_utils import setup_logger

# Set up logger
logger = setup_logger(__name__)

@retry_with_exponential_backoff()
def generate_slides(state: Dict) -> Dict:
    """Generate presentation slides from processed content."""
    try:
        logger.info("Starting slide generation...")
        
        # Get required paths
        deck_dir = Path(state["deck_info"]["path"])
        ai_dir = deck_dir / "ai"
        
        # Load processed summaries
        summaries_path = ai_dir / "processed_summaries.md"
        if not summaries_path.exists():
            raise FileNotFoundError("Processed summaries not found")
            
        with open(summaries_path, "r") as f:
            content = f.read()
            
        # Initialize model
        model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=4096,
            temperature=0.7
        )
        
        # Create prompt
        messages = [
            SystemMessage(content="""You are an expert at creating clear and engaging presentation slides.
            Convert the provided content into a well-structured presentation outline.
            
            Follow these guidelines:
            1. Create clear section breaks
            2. Maintain all specific benefit amounts
            3. Keep tables in their original format
            4. Use clear hierarchy in content
            5. Preserve all plan details exactly"""),
            HumanMessage(content=f"Convert this content into a presentation outline:\n\n{content}")
        ]
        
        # Generate slides
        response = model.invoke(messages)
        slides_content = response.content
        
        # Save slides
        slides_path = ai_dir / "slides.md"
        with open(slides_path, "w") as f:
            f.write(slides_content)
            
        logger.info("Successfully generated slides")
        return state
        
    except Exception as e:
        logger.error(f"Failed to generate slides: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "generate_slides"
        }
        return state 