"""Audio generation node for the builder agent."""
import json
import logging
from pathlib import Path
from typing import Dict, List
from openai import AsyncOpenAI
from ..state import BuilderState
from ...utils.content import save_content
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

@traceable(name="setup_audio")
async def setup_audio(state: Dict) -> Dict:
    """Sets up audio configuration and generates script"""
    try:
        logger.info("Starting audio setup")
        
        # Get paths
        base_dir = Path(__file__).parent.parent.parent.parent
        template_path = base_dir / "decks" / state["metadata"]["template"] / "audio" / "audio_script.md"
        deck_dir = Path(state["deck_info"]["path"])
        script_path = deck_dir / "audio" / "audio_script.md"
        config_path = deck_dir / "audio" / "audio_config.json"
        
        # Load template
        with open(template_path) as f:
            template = f.read()
            
        # Check if script already exists
        existing_content = ""
        if script_path.exists():
            with open(script_path, "r") as f:
                existing_content = f.read()
                logger.info("Found existing script content")
        
        # Create messages for script generation
        messages = [
            {
                "role": "system",
                "content": """You are an expert at creating presentation scripts.
                
                Guidelines for script content:
                - Keep the tone professional but conversational
                - Each section should be marked with **Section Title**
                - Each v-click point should have its own paragraph
                - Maintain natural transitions between sections
                - Include clear verbal cues for slide transitions
                - Do not wrap the content in ```markdown or ``` tags"""
            },
            {
                "role": "user",
                "content": f"""
                {"Use this existing script structure as your base - maintain all sections and formatting:" if existing_content else "Use this template structure - notice the section formatting:"}
                {existing_content if existing_content else template}
                
                Generate a script using this processed summary content:
                {state["processed_summaries"]}
                
                {"Update the content while maintaining the exact same structure and formatting from the existing script." if existing_content else "Maintain all section formatting and structure from the template."}
                Do not wrap the content in ```markdown or ``` tags.
                """
            }
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=8000
        )
        
        # Get script content
        script_content = response.choices[0].message.content
        
        # Save script
        await save_content(script_path, script_content)
        
        # Create/update config
        config = {
            "title": state["metadata"]["title"],
            "script_path": str(script_path.relative_to(deck_dir)),
            "slide_count": len(state.get("summaries", []))
        }
        
        # Save config
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            
        # Update state
        state["audio_config"] = config
        state["script"] = script_content  # Add script content to state
        logger.info("Completed audio setup")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in setup_audio: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        state["error_context"] = {
            "step": "setup_audio",
            "error": str(e)
        }
        return state 