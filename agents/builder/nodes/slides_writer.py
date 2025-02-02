"""Slide generation node for the builder agent."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from openai import AsyncOpenAI
from ..state import BuilderState
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

def get_page_references(summaries: List[Dict]) -> Tuple[List[str], List[str]]:
    """Extract page references for tables and limitations."""
    pages_with_tables = []
    pages_with_limitations = []
    
    for s in summaries:
        page_num = s.get('page')
        if not page_num:
            continue
            
        page_path = f"/img/pages/page_{page_num}.png"
        table_details = s.get("tableDetails", {})
        
        if table_details.get("hasBenefitsTable"):
            pages_with_tables.append(page_path)
        if table_details.get("hasLimitations"):
            pages_with_limitations.append(page_path)
    
    return pages_with_tables, pages_with_limitations

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
                "content": """You are an expert presentation designer specializing in insurance benefits.
                
                Guidelines for slide content:
                1. Slide Structure:
                   - Keep ALL existing slides that don't have validation issues
                   - Only modify slides specifically mentioned in validation issues
                   - Each slide must maintain its existing layout and transition

                2. Content Formatting:
                   - Use <v-click> for each bullet point
                   - Bold key terms with **term**
                   - Include arrows for benefit amounts
                   - Keep existing slide titles and headers
                   - Maintain existing slide order

                3. Validation Rules:
                   - Each bullet must be in its own <v-click> tag
                   - Benefits must include arrow components
                   - No use of word "comprehensive"
                   - Keep exact section titles from script"""
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
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.125,
            max_tokens=8000
        )
        
        # Get updated middle slides
        updated_middle_slides = response.choices[0].message.content.strip()
        
        # Reconstruct full slides content
        slides_content = f"{first_slide}\n{updated_middle_slides}\n{last_slide}".strip()
        
        # Save to file
        output_path = Path(state["deck_info"]["path"]) / "slides.md"
        await save_content(output_path, slides_content)
        
        # Update state
        state["slides"] = slides_content
        state["slide_count"] = count_slides(slides_content)
        
        logger.info(f"Updated {len(sections_to_fix)} slides with validation issues")
        return state
        
    except Exception as e:
        logger.error(f"Error in slides_writer: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "slide_generation"
        }
        return state 