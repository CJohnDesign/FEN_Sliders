"""Validator node for checking and fixing slide-script synchronization."""
import json
import logging
from typing import Dict, List
from pathlib import Path
from openai import AsyncOpenAI
from ..state import BuilderState
from ...utils.content import save_content
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

@traceable(name="validate_and_fix")
async def validate_and_fix(state: Dict) -> Dict:
    """Validate and fix synchronization between slides and script."""
    logger.info("Starting validation and synchronization check")
    
    try:
        # Get paths
        deck_dir = Path(state["deck_info"]["path"])
        slides_path = deck_dir / "slides.md"
        script_path = deck_dir / "audio" / "audio_script.md"
        
        # Read files
        with open(slides_path) as f:
            slides_content = f.read()
        with open(script_path) as f:
            script_content = f.read()
            
        # Create messages for validation
        messages = [
            {
                "role": "system",
                "content": """You are an expert at validating presentation slides and scripts.
                
                Focus on these key aspects:
                1. Each <v-click> in the slides must have a corresponding point in the script
                2. There must be an additional line BEFORE the first v-click in each section to describe the initial state
                3. Script points should follow the same order as v-clicks
                4. Each v-click point should have its own paragraph in the script
                5. Maintain natural transitions between points
                
                If fixes are needed, return a JSON object with:
                {
                    "needs_fixes": true/false,
                    "fixed_slides": "complete fixed slides content if needed",
                    "fixed_script": "complete fixed script content if needed",
                    "changes_made": ["list of changes made"]
                }
                
                Example of proper synchronization:
                
                Slides:
                # Benefits
                
                <v-click>
                **Primary Care** - $25 copay
                </v-click>
                
                <v-click>
                **Specialist** - $40 copay
                </v-click>
                
                Script:
                **Benefits**
                
                Let's look at the benefits included in this plan.
                
                Primary care visits have a $25 copay, making regular checkups affordable.
                
                For specialist visits, you'll have a $40 copay when you need expert care."""
            },
            {
                "role": "user",
                "content": f"""Please validate and fix the synchronization between these slides and script:

Slides:
{slides_content}

Script:
{script_content}

Focus on ensuring:
1. Each <v-click> has a matching script point
2. There's always a line before the first v-click
3. Points are in the same order
4. Each point has its own paragraph"""
            }
        ]
        
        # Get model response
        logger.info("Sending request to model")
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=8000
        )
        
        # Parse response
        try:
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content.replace("```json", "", 1)
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            fixes = json.loads(content)
            logger.info("Successfully parsed model response")
            
            # Apply fixes if needed
            if fixes.get("needs_fixes", False):
                logger.info("Applying fixes to slides and script")
                logger.info("Changes to make: " + ", ".join(fixes.get("changes_made", [])))
                
                # Update slides
                if fixes.get("fixed_slides"):
                    await save_content(slides_path, fixes["fixed_slides"])
                    logger.info("Updated slides file")
                    
                # Update script
                if fixes.get("fixed_script"):
                    await save_content(script_path, fixes["fixed_script"])
                    logger.info("Updated script file")
            else:
                logger.info("No fixes needed - slides and script are properly synchronized")
            
            # Update state
            state["validation_result"] = fixes
            logger.info("Completed validation and synchronization check")
            
            return state
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing model response: {str(e)}")
            logger.error(f"Raw response: {response.content}")
            raise
            
    except Exception as e:
        logger.error(f"Error in validate_and_fix: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "validation"
        }
        return state 