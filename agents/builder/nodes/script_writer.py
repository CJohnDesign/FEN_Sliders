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
                "content": """You are an expert script writer for presentations. Format scripts according to these rules:

                1. Section Headers:
                   - Must use exact format: ---- Section Title ----
                   - Add blank line before and after header
                   - Example:

                   ---- Plan Benefits ----

                   Let's review the benefits available in this plan.

                2. Line Break Rules:
                   - Each line must correspond to one v-click in slides
                   - Add blank line between each script line
                   - First line introduces the section
                   - Example:

                   ---- Plan Benefits ----

                   Let's review the benefits available in this plan.

                   The hospital confinement benefit provides coverage for your stay.

                   Primary care visits are also covered under this plan.

                3. Script to Slide Mapping:
                   ```
                   Script:
                   ---- Plan Benefits ----

                   Let's review the benefits available in this plan.

                   The hospital confinement benefit provides coverage for your stay.

                   Primary care visits are also covered under this plan.

                   Slides:
                   ## Plan Benefits

                   Let's review the benefits available in this plan.

                   <v-click>

                   **Hospital Confinement Benefit**
                   Coverage for your stay
                   </v-click>

                   <v-click>

                   **Primary Care Visits**
                   Coverage for doctor visits
                   </v-click>
                   ```

                4. Number Formatting:
                   - Write numbers as words
                   - "fifty dollars" not "$50"
                   - "twenty-four/seven" not "24/7"
                   - "one hundred" not "100"

                5. Verbal Flow:
                   - Use natural speech patterns
                   - Clear transitions between points
                   - One idea per line
                   - Avoid words like "comprehensive"

                6. Closing Format:
                   - Thank the audience
                   - Summarize key points
                   - Must end with "Continue to be great!"
                   """
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

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.125
        )
        
        # Clean any markdown code block markers
        formatted_script = response.choices[0].message.content.replace('```markdown', '').replace('```', '').strip()
        logger.info("Successfully formatted script")
        
        # Save the formatted script
        deck_dir = Path(state["deck_info"]["path"])
        script_path = deck_dir / "audio" / "audio_script.md"
        await save_content(script_path, formatted_script)
        
        state["script"] = formatted_script
        return state
        
    except Exception as e:
        logger.error(f"Error formatting script: {str(e)}")
        state["error_context"] = {
            "step": "script_writer",
            "error": str(e)
        }
        return state 