"""Validator node for checking and fixing slide-script synchronization."""
import json
import logging
import os
import re
from typing import Dict, List, Tuple
from pathlib import Path
from openai import AsyncOpenAI
from ..state import BuilderState
from ...utils.content import save_content
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

def parse_sections(content: str) -> List[Tuple[str, str, int, int]]:
    """Parse content into sections based on ## headers and frontmatter.
    Returns list of (title, content, start_line, end_line) tuples.
    Special handling for cover slide with frontmatter."""
    lines = content.split('\n')
    sections = []
    current_title = None
    current_content = []
    start_line = 0
    
    # First, check if we start with frontmatter (cover slide)
    if lines and lines[0].strip() == '---':
        # Find the end of frontmatter
        end_frontmatter = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_frontmatter = i
                break
                
        if end_frontmatter != -1:
            # Collect all content up to the first ## header
            cover_content = []
            i = 0
            while i < len(lines):
                if lines[i].startswith('## '):
                    break
                cover_content.append(lines[i])
                i += 1
                
            if cover_content:
                sections.append((
                    "Cover",
                    '\n'.join(cover_content),
                    0,
                    i
                ))
                start_line = i
    
    # Process the rest of the sections
    current_section_start = start_line
    for i in range(start_line, len(lines)):
        line = lines[i]
        if line.startswith('## '):
            if current_title:
                sections.append((
                    current_title,
                    '\n'.join(current_content),
                    current_section_start,
                    i
                ))
            current_title = line[3:].strip()
            current_content = [line]
            current_section_start = i
        else:
            if current_title:
                current_content.append(line)
            
    # Handle last section
    if current_title:
        sections.append((
            current_title,
            '\n'.join(current_content),
            current_section_start,
            len(lines)
        ))
        
    return sections

def get_corresponding_script_section(script_content: str, section_title: str) -> Tuple[str, int, int]:
    """Find the corresponding script section for a slide section."""
    lines = script_content.split('\n')
    section_marker = f"---- {section_title} ----"
    
    start_idx = -1
    end_idx = -1
    
    for i, line in enumerate(lines):
        if line.strip() == section_marker:
            start_idx = i
        elif start_idx != -1 and line.startswith('----'):
            end_idx = i
            break
            
    if start_idx != -1:
        if end_idx == -1:
            end_idx = len(lines)
        return '\n'.join(lines[start_idx:end_idx]), start_idx, end_idx
    return "", 0, 0

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
        
        # Get image paths
        image_paths = get_image_paths(deck_dir, use_descriptive_names=True)
        logger.info("Available page images: " + ", ".join(image_paths["pages"]))
        logger.info("Available logos: " + ", ".join(image_paths["logos"]))
        
        # Read files
        with open(slides_path) as f:
            slides_content = f.read()
        with open(script_path) as f:
            script_content = f.read()
            
        # Parse into sections
        slide_sections = parse_sections(slides_content)
        logger.info(f"Found {len(slide_sections)} sections to validate")
        
        # Process each section
        all_fixes = []
        fixed_slides = []
        current_script = script_content
        
        # Add cover slide (first section) without validation
        if slide_sections:
            cover_section = slide_sections[0]
            logger.info("Preserving cover slide without validation")
            fixed_slides.append(cover_section[1])  # Add the content
        
        # Process middle sections (excluding first and last)
        for idx, (section_title, section_content, start_line, end_line) in enumerate(slide_sections[1:-1], 1):
            logger.info(f"Processing section {idx} of {len(slide_sections) - 2}: {section_title}")
            
            # Initialize section content
            current_section = section_content
            needs_more_fixes = True
            validation_attempts = 0
            max_validation_attempts = 3  # Prevent infinite loops
            
            # Keep validating until no more fixes needed or max attempts reached
            while needs_more_fixes and validation_attempts < max_validation_attempts:
                validation_attempts += 1
                logger.info(f"Validation attempt {validation_attempts} for section: {section_title}")
                
                # Get corresponding script section
                script_section, script_start, script_end = get_corresponding_script_section(
                    current_script, section_title
                )
                
                # Create messages for section validation
                messages = [
                    {
                        "role": "system",
                        "content": """You are an expert at validating presentation slides and scripts.
                        
                        Focus on these key aspects:
                        1. Each <v-click> in the slides must have a corresponding point in the script
                            A. There must be an additional line in each script
                            B. The first line of the script should speak to the headline of the slide
                        2. Script points should follow the same order as v-clicks
                        3. Each v-click point should have its own line in the script
                            A. A single sentence can be broken into multiple lines in the script
                            B. Maintain narrative flow as if the new line wasn't even there
                        4. Maintain natural transitions between points in the script but descriptive bullets in the slides
                        5. Insert appropriate image paths in slide frontmatter where they match the content
                        6. Insert provider logos when their benefits are mentioned
                            A. when adding a logo, it should share a v-click tag with the related benefit text
                        7. NEVER use the word "comprehensive" anywhere in the content
                           - This word is strictly prohibited
                           - Do not use it to describe plans, benefits, coverage, or anything else
                           - Replace any instances with more specific descriptions
                        
                        When editing slides:
                            - Do not change the layout of the slide
                            - Keep bullets short and concise
                            - Show number and dollar amounts using numbers, eg $150 / 3 Days
                            - Keep slides content in order
                            - Use generous capitalization, like title case
                    
                        When editing script:
                            - maintain the narrative flow of the script for a voice over recording
                            - Always spell out numberic values.
                            - Never itemize or bullet content, always return sentences
                            - Again, we are adding interjecting new lines to the script inrelation to the cooresponding v-click content on the slide
                                          
                        When inserting page images:
                        - Look at the descriptive filenames to match content
                        - Add page images in frontmatter: `image: img/pages/01_basic_core_and_core-plus_benefits.png`
                        - Only insert page images where content clearly matches
                        - if a slide header includes an image, because we found a page that made sense of that page, set the layout to `one-half-img`
                        - if a slide header does not include an image, don't adjust the layout setting

                        When editing a plan tier:
                        - Always give clear and complete information about the plan tier
                        - Script should mention all benefits and features of the plan tier
                        - Slides should itemize the benefits and features of the plan tier

                        When inserting logos:
                        - Add provider logos when their benefits are mentioned
                        - Wrap logos in the same v-click with the related benefit text
                        - Use the correct logo path from the available logos
                        - IMPORTANT: All logo paths must start with ./ (e.g., ./img/logos/provider_logo.png)
                        - Use this format for logos:
                          <v-click>
                          **Benefit Name** through Provider
                          <div class="grid grid-cols-1 gap-4 items-center px-8 py-4">
                            <img src="./img/logos/provider_logo.png" class="h-12 mix-blend-multiply" alt="Provider Logo">
                          </div>
                          </v-click>
                          Note: the FirstEnroll logo is ./img/logos/FEN_logo.svg  // no trailing . needed
                        
                        If fixes are needed, return a JSON object with:
                        {
                            "needs_fixes": true/false,
                            "fixed_slides": "complete fixed slides content if needed",
                            "fixed_script": "complete fixed script content if needed",
                            "changes_made": ["list of changes made"]
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"""Please validate and fix the synchronization for section {idx} of {len(slide_sections) - 2}:

Title: {section_title}

Available images to insert where appropriate:

Page Images (use these descriptive names only):
{json.dumps(image_paths["pages"], indent=2)}

Logo Images (always prefix with ./):
{json.dumps(image_paths["logos"], indent=2)}

Slides Section:
{current_section}

Script Section:
{script_section}

Focus on ensuring:
1. Each <v-click> has a matching script point
2. There's always a line before the first v-click
3. Points are in the same order
4. Each point has its own paragraph
5. Insert appropriate page images in frontmatter where content matches
6. Insert provider logos when their benefits are mentioned (with ./ prefix)
7. Remove ANY use of the word "comprehensive"
8. Ensure each slide has logical v-clicks
9. Maintain formatting of slides and slide headers"""
                    }
                ]
                
                # Get model response for section
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4000
                )
                
                try:
                    content = response.choices[0].message.content
                    if content.startswith("```json"):
                        content = content.replace("```json", "", 1)
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    fixes = json.loads(content)
                    
                    if fixes.get("needs_fixes", False):
                        logger.info(f"Found fixes needed in attempt {validation_attempts} for section: {section_title}")
                        all_fixes.extend(fixes.get("changes_made", []))
                        
                        # Update current section content for next iteration
                        current_section = fixes.get("fixed_slides", current_section)
                        if fixes.get("fixed_script"):
                            # Update script sections
                            script_lines = current_script.split('\n')
                            script_lines[script_start:script_end] = fixes["fixed_script"].split('\n')
                            current_script = '\n'.join(script_lines)
                            
                        needs_more_fixes = True
                    else:
                        logger.info(f"No more fixes needed for section: {section_title}")
                        needs_more_fixes = False
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing model response for section {section_title}: {str(e)}")
                    needs_more_fixes = False
            
            # Add final version of section
            fixed_slides.append(current_section)
            if validation_attempts >= max_validation_attempts:
                logger.warning(f"Reached max validation attempts for section: {section_title}")
        
        # Add closing slide (last section) without validation
        if len(slide_sections) > 1:
            closing_section = slide_sections[-1]
            logger.info("Preserving closing slide without validation")
            fixed_slides.append(closing_section[1])  # Add the content
                
        # Combine all fixed content
        final_slides = '\n\n'.join(fixed_slides)
        
        # Save files if changes were made
        if all_fixes:
            await save_content(slides_path, final_slides)
            await save_content(script_path, current_script)
            logger.info(f"Applied {len(all_fixes)} fixes across all sections")
            
        # Update state
        state["validation_result"] = {
            "needs_fixes": bool(all_fixes),
            "changes_made": all_fixes
        }
        logger.info("Completed validation and synchronization check")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in validate_and_fix: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "validation"
        }
        return state 