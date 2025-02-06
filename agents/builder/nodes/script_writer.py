"""Script writer node for the builder agent."""
import json
import logging
import os
from pathlib import Path
from string import Template
from openai import AsyncOpenAI
from ..state import BuilderState, ValidationIssues, ValidationIssue
from ...utils.content import save_content
from ..utils.content_parser import parse_script_sections
from ..utils.logging_utils import log_error
from langsmith.run_helpers import traceable
from ..prompts.script_writer_prompts import (
    SCRIPT_WRITER_SYSTEM_PROMPT,
    SCRIPT_WRITER_HUMAN_PROMPT
)
from ...utils.llm_utils import get_llm

# Set up logging
logger = logging.getLogger(__name__)

def save_script_to_file(script_content: str, deck_path: str) -> bool:
    """Save script content to file."""
    try:
        deck_path = Path(deck_path)
        script_path = deck_path / "audio" / "audio_script.md"
        
        # Ensure directory exists
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        with open(script_path, "w") as f:
            f.write(script_content)
            
        logger.info(f"Saved script to {script_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save script: {str(e)}")
        return False

def escape_curly_braces(text: str) -> str:
    """Double up curly braces to escape them in f-strings."""
    return text.replace("{", "{{").replace("}", "}}")

def filter_validation_issues(issues: ValidationIssues) -> str:
    """Filter and format validation issues specific to script."""
    if not issues or not issues.script_issues:
        return ""
        
    script_issues = []
    for issue in issues.script_issues:
        script_issues.append(f"- In section '{issue.section}': {issue.issue}")
        if issue.suggestions:
            script_issues.extend([f"  * {suggestion}" for suggestion in issue.suggestions])
    
    return "\nFix these validation issues:\n" + "\n".join(script_issues) if script_issues else ""

async def create_script_chain():
    """Create the chain for generating script content."""
    # Use centralized LLM configuration
    llm = await get_llm(temperature=0.2)
    return llm

@traceable(name="script_writer")
async def script_writer(state: BuilderState) -> BuilderState:
    """Update script based on validation issues and suggestions."""
    try:
        # Get current script content and validation issues
        current_script = state.script if hasattr(state, 'script') else ""
        validation_issues = state.validation_issues if hasattr(state, 'validation_issues') else None
        
        # Check if we need to create initial script
        needs_initial_script = (
            not current_script and 
            state.slides  # We have slides to work with
        )
        
        if needs_initial_script:
            logger.info("Creating initial script content")
            
            # Create messages for initial script
            messages = [
                {
                    "role": "system",
                    "content": SCRIPT_WRITER_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": SCRIPT_WRITER_HUMAN_PROMPT.format(
                        template="",  # No template for initial generation
                        processed_summaries="",  # No summaries for initial generation
                        slides_content=state.slides
                    )
                }
            ]
            
            # Create and run chain
            chain = await create_script_chain()
            response = await chain.ainvoke(messages)
            
            # Extract script content
            state.script = response.content if hasattr(response, 'content') else str(response)
            logger.info("Created initial script content")
            
            # Save initial script to file
            if state.deck_info and state.deck_info.path:
                script_path = Path(state.deck_info.path) / "audio" / "audio_script.md"
                script_path.parent.mkdir(parents=True, exist_ok=True)
                await save_content(script_path, state.script)
                logger.info(f"Saved initial script to {script_path}")
                
            return state
            
        # If no content to fix, return current state
        if not current_script:
            logger.info("No script content to fix")
            return state
            
        # Format validation issues for the prompt
        validation_instructions = filter_validation_issues(validation_issues) if validation_issues else ""
        
        # Get suggested fixes if available
        suggested_fixes = validation_issues.suggested_fixes if hasattr(validation_issues, 'suggested_fixes') else {}
        suggested_script_fixes = suggested_fixes.get('script', '')
        
        # Create messages for script update
        messages = [
            {
                "role": "system",
                "content": SCRIPT_WRITER_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": SCRIPT_WRITER_HUMAN_PROMPT.format(
                    template=current_script,
                    processed_summaries="",  # No summaries needed for fixes
                    slides_content=state.slides
                ) + "\n\n" + validation_instructions + (
                    "\n\nSuggested fixes:" + suggested_script_fixes if suggested_script_fixes else ""
                )
            }
        ]

        # Create and run chain
        chain = await create_script_chain()
        response = await chain.ainvoke(messages)
        
        # Extract updated script content
        updated_script = response.content if hasattr(response, 'content') else str(response)
        
        # Verify changes were made
        if updated_script != current_script:
            logger.info("Script content updated")
            state.script = updated_script
            
            # Save script to file
            if state.deck_info and state.deck_info.path:
                script_path = Path(state.deck_info.path) / "audio" / "audio_script.md"
                script_path.parent.mkdir(parents=True, exist_ok=True)
                await save_content(script_path, updated_script)
                logger.info(f"Successfully saved updated script to {script_path}")
        else:
            logger.warning("No changes made to script content")
            
        return state
            
    except Exception as e:
        log_error(state, "script_writer", e)
        state.error_context = {
            "error": f"Failed to fix script: {str(e)}",
            "stage": "validation"
        }
        return state 