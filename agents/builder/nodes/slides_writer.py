"""Slide generation node for the builder agent."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from openai import AsyncOpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, SlideContent
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

def filter_validation_issues(issues: Dict) -> str:
    """Filter and format validation issues specific to slides."""
    if not issues or 'slide_issues' not in issues:
        return ""
        
    slides_issues = []
    for issue in issues['slide_issues']:
        slides_issues.append(f"- In section '{issue.get('section', '')}': {issue.get('issue', '')}")
    
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
        current_slides = state.get("slides", "")  # This is the validated content from validator
        validation_issues = state.get("validation_issues", {})
        
        # If no content or no issues, return current state
        if not current_slides or not validation_issues.get('slide_issues'):
            logger.info("No slides content or no issues to fix")
            return state
            
        # Extract preserved slides
        first_slide, middle_slides, last_slide = extract_preserved_slides(current_slides)
        
        # Split middle slides into individual slides
        middle_slide_sections = middle_slides.split('---') if middle_slides else []
        
        # Get list of sections that need fixing
        sections_to_fix = {issue['section'] for issue in validation_issues.get('slide_issues', [])}
        
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

        # Create slides chain
        chain = create_slides_chain()
        
        # Generate slides content
        slides_content = await chain.ainvoke({
            "template": state.deck_info.template,
            "processed_summaries": state.processed_summaries
        })
        
        # Write slides to file
        output_path = Path(state.deck_info.path) / "slides.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(slides_content.content)
            
        # Update state
        state.slides = slides_content.content
        
        # Create structured slides
        structured_slides = []
        sections = slides_content.content.split("---")
        for i, section in enumerate(sections):
            if section.strip():
                # Extract title from the section if it exists
                lines = section.strip().split("\n")
                title = next((line.replace("#", "").strip() for line in lines if line.startswith("#")), f"Slide {i + 1}")
                
                slide = SlideContent(
                    page_number=i + 1,
                    title=title,
                    content=section.strip()
                )
                structured_slides.append(slide)
                
        state.structured_slides = structured_slides
        
        # Log completion
        log_state_change(
            state=state,
            node_name="slides_writer",
            change_type="complete",
            details={
                "slide_count": len(structured_slides),
                "output_path": str(output_path)
            }
        )
        
        return state
        
    except Exception as e:
        log_error(state, "slides_writer", e)
        state.error_context = {
            "error": str(e),
            "stage": "slides_writing"
        }
        return state 