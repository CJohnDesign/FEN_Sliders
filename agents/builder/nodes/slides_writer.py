"""Slide generation node for the builder agent."""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
from openai import AsyncOpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, SlideContent, ValidationIssues, ValidationIssue
from ..utils.logging_utils import log_state_change, log_error
from ..config.models import get_model_config
from ...utils.llm_utils import get_llm
from ..prompts.slides_writer_prompts import SLIDES_WRITER_PROMPT
from ...utils.content import save_content, count_slides
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

def extract_preserved_slides(content: str) -> Tuple[str, str, str]:
    """Extract first and last slides to preserve them, returning the current content to update."""
    # Clean any markdown tags first
    content = content.replace('```markdown', '').replace('```', '').strip()
    
    slides = content.split('---')
    if len(slides) <= 2:  # No content or just frontmatter
        return "", "", ""
    
    # Clean and format first slide (includes frontmatter)
    first_slide = slides[0] + "\n---\n" + slides[1].strip()
    
    # Clean and format last slide
    last_slide = slides[-1].strip()
    last_slide = f"---\n{last_slide}" if last_slide else ""
    
    # Join middle slides with proper separators
    current_slides = "\n---\n".join(slides[2:-1]) if len(slides) > 3 else ""
    
    return first_slide, current_slides, last_slide

def filter_validation_issues(issues: ValidationIssues) -> str:
    """Filter and format validation issues specific to slides."""
    if not issues or not issues.slide_issues:
        return ""
        
    slides_issues = []
    for issue in issues.slide_issues:
        slides_issues.append(f"- In section '{issue.section}': {issue.issue}")
    
    return "\nFix these validation issues:\n" + "\n".join(slides_issues) if slides_issues else ""

def create_slides_chain():
    """Create the chain for generating slides content."""
    # Use centralized LLM configuration
    llm = get_llm(temperature=0.2)
    
    # Create prompt template using imported prompts
    prompt = ChatPromptTemplate.from_messages([
        ("system", PROCESS_SLIDES_PROMPT),
        ("human", PROCESS_SLIDES_HUMAN_TEMPLATE)
    ])
    
    # Create chain
    chain = prompt | llm
    
    return chain

def save_slides_to_file(slides_content: str, deck_path: str) -> bool:
    """Save slides content to file."""
    try:
        deck_path = Path(deck_path)
        slides_path = deck_path / "slides.md"
        
        # Ensure directory exists
        deck_path.mkdir(parents=True, exist_ok=True)
        
        # Write content
        with open(slides_path, "w") as f:
            f.write(slides_content)
            
        logger.info(f"Saved slides to {slides_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save slides: {str(e)}")
        return False

@traceable(name="slides_writer")
async def slides_writer(state: BuilderState) -> BuilderState:
    """Update slides based on validation issues and suggestions."""
    try:
        # Get current slides content and validation issues
        current_slides = state.slides if hasattr(state, 'slides') else ""
        validation_issues = state.validation_issues if hasattr(state, 'validation_issues') else None
        
        # If no content to fix, return current state
        if not current_slides:
            logger.info("No slides content to fix")
            return state
            
        # Format validation issues for the prompt
        validation_instructions = filter_validation_issues(validation_issues) if validation_issues else ""
        
        # Get suggested fixes if available
        suggested_fixes = validation_issues.suggested_fixes if hasattr(validation_issues, 'suggested_fixes') else {}
        suggested_slides_fixes = suggested_fixes.get('slides', '')
        
        # Create messages for slide update
        messages = [
            {
                "role": "system",
                "content": SLIDES_WRITER_PROMPT
            },
            {
                "role": "user",
                "content": f"""Review and update these slides based on the validation issues and suggestions:

Current slides:
{current_slides}

{validation_instructions}

{"Suggested fixes:" + suggested_slides_fixes if suggested_slides_fixes else ""}

Instructions:
1. Return the complete updated slides
2. Address all validation issues and suggestions
3. Maintain consistent formatting and structure
4. Keep all slide transitions and layouts
5. Ensure proper slide order and flow
6. Preserve any existing frontmatter
7. Keep the first slide (title) and last slide intact
"""
            }
        ]

        # Create and run chain
        llm = await get_llm(temperature=0.2)
        response = await llm.ainvoke(messages)
        
        # Extract updated slides content
        updated_slides = response.content if hasattr(response, 'content') else str(response)
        
        # Verify changes were made
        if updated_slides != current_slides:
            logger.info("Slides content updated")
            state.slides = updated_slides
            
            # Save slides to file
            if state.deck_info and state.deck_info.path:
                slides_path = Path(state.deck_info.path) / "slides.md"
                await save_content(slides_path, updated_slides)
                logger.info(f"Successfully saved slides to {slides_path}")
        else:
            logger.warning("No changes made to slides content")
            
        return state
        
    except Exception as e:
        log_error(state, "slides_writer", e)
        state.error_context = {
            "error": f"Failed to fix slides: {str(e)}",
            "stage": "validation"
        }
        return state 