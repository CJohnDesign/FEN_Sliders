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
from ..utils.content_parser import Section, parse_script_sections, parse_slides_sections, update_state_with_content
from .script_writer import script_writer
from .slides_writer import slides_writer

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()


def parse_sections(content: str) -> List[Tuple[str, str, str, int, int]]:
    """Parse content into sections based on ## headers and frontmatter.
    Returns list of (title, header_block, content, start_line, end_line) tuples.
    Each slide should have exactly:
    1. A header block (between --- markers) with layout/transition
    2. A content block with heading and v-clicks"""
    
    lines = content.split('\n')
    sections = []
    current_title = None
    current_header = []
    current_content = []
    start_line = 0
    in_header = False
    
    # Handle cover slide specially
    if lines and lines[0].strip() == '---':
        # Find the end of frontmatter
        end_frontmatter = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_frontmatter = i
                break
                
        if end_frontmatter != -1:
            # Include the entire header block including both --- markers
            cover_header = lines[:end_frontmatter + 1]
            remaining_content = []
            i = end_frontmatter + 1
            while i < len(lines):
                if lines[i].startswith('## '):
                    break
                remaining_content.append(lines[i])
                i += 1
                
            sections.append((
                "Cover",
                '\n'.join(cover_header),
                '\n'.join(remaining_content),
                0,
                i
            ))
            start_line = i
            current_header = []  # Reset header after cover
    
    # Process remaining sections
    i = start_line
    while i < len(lines):
        line = lines[i].strip()
        
        # Track header blocks
        if line == '---':
            if not in_header:  # Start of header block
                current_header = [lines[i]]  # Start fresh header block
                in_header = True
            else:  # End of header block
                current_header.append(lines[i])
                in_header = False
            i += 1
            continue
            
        # If we're in a header block, collect header lines
        if in_header:
            current_header.append(lines[i])
            i += 1
            continue
            
        # Look for section title - this is where we create new sections
        if line.startswith('## '):
            # Save previous section if we have one
            if current_title:
                sections.append((
                    current_title,
                    '\n'.join(current_header),
                    '\n'.join(current_content),
                    start_line,
                    i
                ))
                # Reset everything for new section
                current_content = []
                current_header = []  # Reset header for new section
                start_line = i
            
            current_title = line[3:].strip()
            current_content = [lines[i]]
        else:
            current_content.append(lines[i])
            
        i += 1
    
    # Add final section
    if current_title:
        sections.append((
            current_title,
            '\n'.join(current_header),
            '\n'.join(current_content),
            start_line,
            len(lines)
        ))
    
    return sections

def get_script_sections(script_content: str) -> List[Tuple[str, str, str, int, int]]:
    """Extract all script sections with their titles.
    Returns list of (title, header, content, start_line, end_line).
    Script sections have:
    1. Header: The ---- Title ---- line
    2. Content: Everything after the header until the next section"""
    lines = script_content.split('\n')
    sections = []
    current_content = []
    current_start = 0
    current_title = None
    current_header = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith('----') and line.strip().endswith('----'):
            # Save previous section if we have one
            if current_title:  # Only check for title
                sections.append((
                    current_title,
                    current_header or f"---- {current_title} ----",  # Fallback header if missing
                    '\n'.join(current_content),
                    current_start,
                    i
                ))
                current_content = []
            
            # Start new section
            current_title = line.strip()[4:-4].strip()  # Remove ---- markers
            current_header = line.strip()  # Keep the full ---- Title ---- line
            current_start = i
        else:
            current_content.append(line)
    
    # Add final section
    if current_title:  # Only check for title
        sections.append((
            current_title,
            current_header or f"---- {current_title} ----",  # Fallback header if missing
            '\n'.join(current_content),
            current_start,
            len(lines)
        ))
    
    return sections

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
    
    # Get page images - only include properly formatted descriptive names
    pages_dir = deck_dir / "img" / "pages"
    if pages_dir.exists():
        for file in sorted(pages_dir.glob("*.png")):
            # Only include files that match the pattern: dd_descriptive_name.png
            # where dd is a 2-digit number followed by underscore and contains proper descriptive text
            if (file.name[:2].isdigit() and 
                file.name[2] == '_' and 
                # Check for descriptive naming pattern
                any(keyword in file.name.lower() for keyword in [
                    'overview', 'detail', 'benefit', 'feature', 'comparison',
                    'managed_care', 'insurance', 'plan', 'basic_core'
                ])):
                rel_path = file.relative_to(deck_dir)
                image_paths["pages"].append(str(rel_path))
                logger.info(f"Added page image: {str(rel_path)}")
            else:
                logger.warning(f"Skipping non-descriptive page image: {file.name}")
        
        if not image_paths["pages"]:
            logger.warning("No properly formatted descriptive page images found.")
        else:
            logger.info(f"Found {len(image_paths['pages'])} properly formatted page images")
    else:
        logger.warning(f"Pages directory not found: {pages_dir}")
        
    # Get logo images - ensure proper path format
    logos_dir = deck_dir / "img" / "logos"
    if logos_dir.exists():
        for file in sorted(logos_dir.glob("*")):
            if file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.svg']:
                # Always use ./ prefix for logo paths
                rel_path = "./img/logos/" + file.name
                image_paths["logos"].append(rel_path)
                logger.info(f"Added logo: {rel_path}")
        logger.info(f"Found {len(image_paths['logos'])} logo images")
    else:
        logger.warning(f"Logos directory not found: {logos_dir}")
    
    return image_paths

@traceable(name="validate_and_fix")
async def validate_and_fix(state: Dict) -> Dict:
    """Validate synchronization between slides and script."""
    logger.info("Starting validation and synchronization check")
    
    try:
        MAX_RETRIES = 3
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            # Update state with parsed sections
            state = update_state_with_content(state)
            
            # Get script sections
            script_sections = state.get('script_sections', [])
            if not script_sections and state.get('script'):
                script_sections = parse_script_sections(state['script'])
                state['script_sections'] = script_sections
            
            # Get slides sections
            slides_sections = state.get('slides_sections', [])
            if not slides_sections and state.get('slides'):
                slides_sections = parse_slides_sections(state['slides'])
                state['slides_sections'] = slides_sections
            
            # If either is missing, create from the other
            if not script_sections and not slides_sections:
                logger.error("No content found in state")
                state["error_context"] = {
                    "step": "validate_and_fix",
                    "error": "No content found"
                }
                return state
            
            # Validate synchronization
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert content validator. Check synchronization between slides and script according to these rules:

                    1. Content Synchronization
                       - Each section in script has matching slide
                       - Each v-click point has script line
                       - Extra line before v-clicks introducing section
                       - Script can break mid-sentence at v-click points
                       - No "comprehensive" in any content

                    2. Structure Validation
                       - Matching section titles
                       - Proper markdown syntax
                       - Appropriate line breaks

                    3. Plan Tier Structure
                       - Plan name and tier present
                       - Benefits list with details of amounts
                       - Dollar values included

                    Return your response as a JSON object in this format:
                    {
                        "needs_fixes": true/false,
                        "validation_issues": {
                            "script_issues": [
                                {
                                    "section": "section_name",
                                    "issue": "description"
                                }
                            ],
                            "slide_issues": [
                                {
                                    "section": "section_name",
                                    "issue": "description"
                                }
                            ]
                        }
                    }"""
                },
                {
                    "role": "user",
                    "content": f"""Validate these sections and return a JSON response:
                    
                    SCRIPT SECTIONS:
                    {json.dumps([s for s in script_sections], indent=2) if script_sections else "No script sections"}
                    
                    SLIDES SECTIONS:
                    {json.dumps([s for s in slides_sections], indent=2) if slides_sections else "No slides sections"}"""
                }
            ]

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={ "type": "json_object" }
            )
            
            validation_result = json.loads(response.choices[0].message.content)
            
            # Update state with validation results
            state["needs_fixes"] = validation_result["needs_fixes"]
            state["validation_issues"] = validation_result["validation_issues"]
            
            if not validation_result["needs_fixes"]:
                logger.info("Validation passed - no issues found")
                return state
                
            logger.info(f"Found validation issues on attempt {retry_count + 1}")
            
            # Call script_writer if there are script issues
            if validation_result["validation_issues"].get("script_issues"):
                logger.info("Calling script_writer to fix script issues")
                state = await script_writer(state)
            
            # Call slides_writer if there are slide issues
            if validation_result["validation_issues"].get("slide_issues"):
                logger.info("Calling slides_writer to fix slide issues")
                state = await slides_writer(state)
            
            retry_count += 1
            
        logger.warning(f"Reached max retries ({MAX_RETRIES}) - returning current state")
        return state
        
    except Exception as e:
        logger.error(f"Error in validate_and_fix: {str(e)}")
        state["error_context"] = {
            "step": "validate_and_fix",
            "error": str(e)
        }
        return state 