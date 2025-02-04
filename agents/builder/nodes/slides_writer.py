"""Slide generation node for the builder agent."""
import json
import logging
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

@traceable(name="slides_writer")
async def slides_writer(state: BuilderState) -> BuilderState:
    """Update slides that have validation issues while preserving the rest."""
    try:
        # Get current slides content and validation issues
        current_slides = state.get("slides", "")
        validation_issues = state.get("validation_issues")
        
        # If no content or no issues, return current state
        if not current_slides or not validation_issues or not validation_issues.slide_issues:
            logger.info("No slides content or no issues to fix")
            return state
            
        # Extract preserved slides
        first_slide, middle_slides, last_slide = extract_preserved_slides(current_slides)
        
        # Split middle slides into individual slides
        middle_slide_sections = middle_slides.split('---') if middle_slides else []
        
        # Get list of sections that need fixing
        sections_to_fix = {issue.section for issue in validation_issues.slide_issues}
        
        # Format validation issues for the prompt
        validation_instructions = filter_validation_issues(validation_issues)
        
        # Create messages for slide generation
        messages = [
            {
                "role": "system",
                "content": SLIDES_WRITER_PROMPT
            },
            {
                "role": "user",
                "content": f"""Fix ONLY these specific slides that have issues. Keep all other slides exactly as they are:

Current middle slides:
{middle_slides}

Sections that need fixing:
{json.dumps(list(sections_to_fix), indent=2)}

Validation issues to fix:
{validation_instructions}

Instructions:
1. Return ALL middle slides (fixed and unchanged)
2. Only modify the slides for sections listed in validation issues
3. Keep all other slides exactly as they are
4. Maintain the exact same slide order
5. Keep the same transition and layout for each slide
"""
            }
        ]

        # Create and run chain
        chain = create_slides_chain()
        response = await chain.ainvoke({"messages": messages})
        
        # Extract fixed slides content
        fixed_slides = response.content if hasattr(response, 'content') else str(response)
        
        # Combine fixed slides with preserved slides
        if first_slide and last_slide:
            state.slides = f"{first_slide}\n---\n{fixed_slides}\n---\n{last_slide}"
        else:
            state.slides = fixed_slides
            
        return state
        
    except Exception as e:
        log_error(state, "slides_writer", e)
        state.error_context = {
            "error": f"Failed to fix slides: {str(e)}",
            "stage": "validation"
        }
        return state 