"""Validator node for checking and fixing slide-script synchronization."""
import json
import logging
import os
from typing import Dict, List
from pathlib import Path
from openai import AsyncOpenAI
from ..state import BuilderState
from ...utils.content import save_content
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

def get_image_paths(deck_dir: Path, use_descriptive_names: bool = True) -> Dict[str, List[str]]:
    """Get all image paths from img/pages and img/logos directories.
    
    Args:
        deck_dir: Root directory of the deck
        use_descriptive_names: If True, use renamed descriptive filenames, else use original names
    """
    image_paths = {
        "pages": [],
        "logos": []
    }
    
    # Get page images
    pages_dir = deck_dir / "img" / "pages"
    if pages_dir.exists():
        for file in sorted(pages_dir.glob("*.png")):
            # Only include files that match the pattern: dd_descriptive_name.png
            # where dd is a 2-digit number followed by underscore
            if file.name[:2].isdigit() and file.name[2] == '_':
                rel_path = file.relative_to(deck_dir)
                image_paths["pages"].append(str(rel_path))
        
        if not image_paths["pages"]:
            logger.warning("No descriptively named page images found. Images may need to be processed first.")
        else:
            logger.info(f"Found {len(image_paths['pages'])} descriptively named page images")
    else:
        logger.warning(f"Pages directory not found: {pages_dir}")
        
    # Get logo images
    logos_dir = deck_dir / "img" / "logos"
    if logos_dir.exists():
        for file in sorted(logos_dir.glob("*")):
            if file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.svg']:
                # Convert to relative path from deck root with ./ prefix
                rel_path = "./" + str(file.relative_to(deck_dir))
                image_paths["logos"].append(rel_path)
        logger.info(f"Found {len(image_paths['logos'])} logo images")
    else:
        logger.warning(f"Logos directory not found: {logos_dir}")
    
    return image_paths

@traceable(name="validate_and_fix")
async def validate_and_fix(state: Dict) -> Dict:
    """Validate and fix synchronization between slides and script."""
    logger.info("Starting validation and synchronization check")
    
    try:
        # Get paths
        deck_dir = Path(state["deck_info"]["path"])
        slides_path = deck_dir / "slides.md"
        script_path = deck_dir / "audio" / "audio_script.md"
        
        # Get image paths - only descriptively named page images
        image_paths = get_image_paths(deck_dir, use_descriptive_names=True)
        logger.info("Available page images: " + ", ".join(image_paths["pages"]))
        logger.info("Available logos: " + ", ".join(image_paths["logos"]))
        
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
                6. Insert appropriate image paths in slide frontmatter where they match the content
                7. Insert provider logos when their benefits are mentioned
                
                When inserting page images:
                - Look at the descriptive filenames to match content
                - Add page images in frontmatter: `image: img/pages/01_example.png`
                - Only insert page images where content clearly matches
                - Maintain all other frontmatter properties (layout, transition, etc)
                - Only use the descriptively named images provided (starting with numbers like 01_, 02_)
                
                When inserting logos:
                - Add provider logos when their benefits are mentioned
                - Wrap logos in v-click with the related benefit text
                - Use the correct logo path from the available logos
                - IMPORTANT: All logo paths must start with ./ (e.g., ./img/logos/provider_logo.png)
                - Use this format for logos:
                  <v-click>
                  **Benefit Name** through Provider
                  <div class="grid grid-cols-1 gap-4 items-center px-8 py-4">
                    <img src="./img/logos/provider_logo.png" class="h-12 mix-blend-multiply" alt="Provider Logo">
                  </div>
                  </v-click>
                
                If fixes are needed, return a JSON object with:
                {
                    "needs_fixes": true/false,
                    "fixed_slides": "complete fixed slides content if needed",
                    "fixed_script": "complete fixed script content if needed",
                    "changes_made": ["list of changes made"]
                }
                
                Example of proper synchronization with images and logos:
                
                Slides:
                ---
                layout: one-half-img
                image: img/pages/01_dental_benefits_coverage.png
                transition: fade-out
                ---
                
                # Dental Benefits
                
                <v-click>
                **Primary Coverage** through Ameritas
                <div class="grid grid-cols-1 gap-4 items-center px-8 py-4">
                  <img src="./img/logos/Ameritas_logo.png" class="h-12 mix-blend-multiply" alt="Ameritas Logo">
                </div>
                </v-click>
                
                <v-click>
                **Specialist** - $40 copay
                </v-click>
                
                Script:
                **Dental Benefits**
                
                Let's look at the dental benefits included in this plan.
                
                Your primary care coverage is provided by Ameritas, ensuring quality dental care.
                
                For specialist visits, you'll have a $40 copay when you need expert care."""
            },
            {
                "role": "user",
                "content": f"""Please validate and fix the synchronization between these slides and script.

Available images to insert where appropriate:

Page Images (use these descriptive names only):
{json.dumps(image_paths["pages"], indent=2)}

Logo Images (always prefix with ./):
{json.dumps(image_paths["logos"], indent=2)}

Slides:
{slides_content}

Script:
{script_content}

Focus on ensuring:
1. Each <v-click> has a matching script point
2. There's always a line before the first v-click
3. Points are in the same order
4. Each point has its own paragraph
5. Insert appropriate page images in frontmatter where content matches
6. Insert provider logos when their benefits are mentioned (with ./ prefix)"""
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