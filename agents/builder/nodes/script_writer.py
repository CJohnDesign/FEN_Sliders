"""Script writer node for the builder agent."""
import json
import logging
from typing import Dict
from pathlib import Path
from openai import AsyncOpenAI
from ..state import BuilderState
from ...utils.content import save_content
from ..utils.content_parser import parse_script_sections
from langsmith.run_helpers import traceable
from ..prompts.script_writer_prompts import SCRIPT_WRITER_PROMPT

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

@traceable(name="script_writer")
async def script_writer(state: Dict) -> Dict:
    """Format script according to rules."""
    logger.info("Starting script formatting")
    
    try:
        # Get current script content
        script_content = state.get('script', '')
        
        # Get validation issues from state
        validation_issues = state.get('validation_issues', {})
        validation_text = ""
        if validation_issues and 'script_issues' in validation_issues:
            for issue in validation_issues['script_issues']:
                validation_text += f"- {issue.get('section', '')}: {issue.get('issue', '')}\n"
        
        # Get corresponding slides content
        slides_content = state.get('slides', '')
        
        messages = [
            {
                "role": "system",
                "content": SCRIPT_WRITER_PROMPT
            },
            {
                "role": "user",
                "content": f"""Current script content:
{script_content}

Validation issues to fix:
{validation_text}

Corresponding slides content:
{slides_content}

Instructions:
1. Return ONLY the raw script content
2. Each line must have blank lines before and after
3. Each section must have proper ---- Title ---- format
4. Write all numbers as words
5. End with "Continue to be great!"
"""
            }
        ]

        # ... rest of existing code ...

        # ... rest of the function ...

    except Exception as e:
        log_error(state, "script_writer", e)
        state.error_context = {
            "error": str(e),
            "stage": "script_writing"
        }
        return state 