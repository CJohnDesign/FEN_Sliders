"""Script writer node for the builder agent."""
import json
import logging
from typing import Dict, List
from pathlib import Path
from string import Template
from openai import AsyncOpenAI
from ..state import BuilderState, ValidationIssues, ValidationIssue
from ...utils.content import save_content
from ..utils.content_parser import parse_script_sections
from ..utils.logging_utils import log_error
from langsmith.run_helpers import traceable
from ..prompts.script_writer_prompts import SCRIPT_WRITER_PROMPT
from ...utils.llm_utils import get_llm

# Set up logging
logger = logging.getLogger(__name__)

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
    
    return "\nFix these validation issues:\n" + "\n".join(script_issues) if script_issues else ""

async def create_script_chain():
    """Create the chain for generating script content."""
    # Use centralized LLM configuration
    llm = await get_llm(temperature=0.2)
    return llm

@traceable(name="script_writer")
async def script_writer(state: BuilderState) -> BuilderState:
    """Update script sections that have validation issues while preserving the rest."""
    try:
        # Get current script content and validation issues
        current_script = state.script if hasattr(state, 'script') else ""
        validation_issues = state.validation_issues if hasattr(state, 'validation_issues') else None
        
        # If no content or no issues, return current state
        if not current_script or not validation_issues or not validation_issues.script_issues:
            logger.info("No script content or no issues to fix")
            return state
            
        # Parse script sections
        script_sections = parse_script_sections(current_script)
        
        # Get list of sections that need fixing
        sections_to_fix = {issue.section for issue in validation_issues.script_issues}
        
        # Format validation issues for the prompt
        validation_instructions = filter_validation_issues(validation_issues)
        
        # Create message template
        message_template = Template('''Fix ONLY these specific script sections that have issues. Keep all other sections exactly as they are:

Current script:
$current_script

Sections that need fixing:
$sections_to_fix

Validation issues to fix:
$validation_instructions

Instructions:
1. Return the complete script with fixed sections
2. Only modify the sections listed in validation issues
3. Keep all other sections exactly as they are
4. Maintain the exact same section order
5. Keep the same formatting and structure
''')

        # Create messages for script generation
        messages = [
            {
                "role": "system",
                "content": SCRIPT_WRITER_PROMPT
            },
            {
                "role": "user",
                "content": message_template.substitute(
                    current_script=escape_curly_braces(current_script),
                    sections_to_fix=escape_curly_braces(json.dumps(list(sections_to_fix), indent=2)),
                    validation_instructions=escape_curly_braces(validation_instructions)
                )
            }
        ]

        # Create and run chain
        chain = await create_script_chain()
        response = await chain.ainvoke(messages)
        
        # Extract fixed script content
        fixed_script = response.content if hasattr(response, 'content') else str(response)
        
        # Update state with fixed script
        state.script = fixed_script
            
        return state
        
    except Exception as e:
        log_error(state, "script_writer", e)
        state.error_context = {
            "error": f"Failed to fix script: {str(e)}",
            "stage": "validation"
        }
        return state 