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
    """Validate and fix synchronization between slides and script."""
    logger.info("Starting validation and synchronization check")
    
    try:
        # Get paths
        deck_dir = Path(state["deck_info"]["path"])
        slides_path = deck_dir / "slides.md"
        script_path = deck_dir / "audio" / "audio_script.md"
        
        # Get image paths
        image_paths = get_image_paths(deck_dir, use_descriptive_names=True)
        
        # Read files
        with open(slides_path) as f:
            slides_content = f.read()
        with open(script_path) as f:
            script_content = f.read()
            
        # Parse all sections first
        script_sections = get_script_sections(script_content)
        slide_sections = parse_sections(slides_content)
        
        # Store sections in state
        state["sections"] = {
            "script": [],  # Will store {title, header, content} for each section
            "slides": []   # Will store {title, header, content} for each section
        }
        
        # First, store all sections in order
        logger.info("Script sections found:")
        for script_idx, (title, header, content, _, _) in enumerate(script_sections):
            logger.info(f"  {script_idx + 1}. {title}")
            state["sections"]["script"].append({
                "title": title,
                "header": header,
                "content": content,
                "original_index": script_idx
            })
            
        logger.info("\nSlide sections found:")
        for slide_idx, (title, header, content, _, _) in enumerate(slide_sections):
            logger.info(f"  {slide_idx + 1}. {title}")
            state["sections"]["slides"].append({
                "title": title,
                "header": header,
                "content": content,
                "original_index": slide_idx
            })
            
        logger.info(f"\nStored {len(state['sections']['script'])} script sections and {len(state['sections']['slides'])} slide sections")
        
        # Process each section for validation/fixes
        all_fixes = []
        
        for section in state["sections"]["script"]:
            title = section["title"]
            logger.info(f"Processing section: {title}")
            
            # Find matching slide section
            matching_slide = next(
                (s for s in state["sections"]["slides"] if s["title"] == title),
                None
            )
            
            # Log image paths for debugging
            logger.info(f"Image paths: {json.dumps(image_paths, indent=2)}")
            
            if matching_slide:
                # Validate and fix this section pair
                messages = [
                    {
                        "role": "system",
                        "content": """You are an expert at validating presentation slides and scripts.
                        
                        Focus on these key aspects:
                        1. Cover slide special rules:
                           - No v-clicks on the cover slide
                           - Cover script should be a single short paragraph
                           - Must use layout: intro
                           - Must include FirstEnroll logo
                        
                        2. V-click synchronization:
                           - Each <v-click> in slides must have a corresponding point in the script
                           - Script must have an extra line BEFORE the first v-click content to introduce the section
                           - Script points must follow same order as v-clicks
                           - Each v-click point must have its own line in the script
                           - There should be one empty line between each script point
                        
                        3. Plan Tier Slide Rules:
                           - Must use layout: one-half-img
                           - Each benefit MUST be in its own individual <v-click> tag
                           - NEVER use <v-clicks> batch tags
                           - Benefits must follow exact format, based on the plan tiers:
                             **Benefit Name**
                             - Per Day: $X, Max: Y Days
                             or for non-daily benefits:
                             **Benefit Name**
                             - Coverage: X%, Max: Y Days
                             or
                             **Benefit Name**
                             - Max Benefit: $X
                           - Every benefit must have a name, amount, and limit
                           - If plan has many benefits, split into (1/2) and (2/2) slides
                           - Each split slide must maintain same image and layout
                           - Add Arrow component after first benefit on each slide:
                             <Arrow v-bind="{ x1:772, y1:60, x2:772, y2:120, color: 'var(--slidev-theme-accent)' }" />
                           
                        4. Plan Tier Script Rules:
                           - Must start with introduction line: "Let's review Plan X" or similar
                           - Each benefit description must be on its own line
                           - Every benefit must include its exact amount and limits in written form
                           - Benefits must be described in same order as slide v-clicks
                           - Use written numbers instead of numerals (e.g., "one hundred" not "100")
                           - One empty line between each benefit description
                           - For split slides, second part must start with "Continuing with Plan X"
                        
                        Example Plan Tier Slide:
                        ```
                        ---
                        transition: fade-out
                        layout: one-half-img
                        image: /img/pages/page_2.png
                        ---
                        
                        ## Plan 200 (1/2)
                        
                        <v-click>
                        
                        **Hospital Confinement Benefit**
                        - Per Day: $200, Max: 30 Days
                        <Arrow v-bind="{ x1:772, y1:60, x2:772, y2:120, color: 'var(--slidev-theme-accent)' }" />
                        </v-click>
                        
                        <v-click>
                        
                        **Primary Care Doctors Office Visit**
                        - Per Day: $50, Max: 5 Days
                        </v-click>
                        
                        <v-click>
                        
                        **Emergency Room Benefit**
                        - Per Day: $50, Max: 1 Day
                        </v-click>
                        
                        <v-click>
                        
                        **Accidental Death Benefit**
                        - Max Benefit: $10,000
                        </v-click>
                        ```
                        
                        Example Plan Tier Script:
                        ```
                        ---- Plan 200 (1/2) ----
                        
                        Let's review Plan 200.
                        
                        The hospital confinement benefit provides two hundred dollars per day for up to thirty days.
                        
                        For doctor visits, you'll receive fifty dollars per day for up to five days.
                        
                        The emergency room benefit covers fifty dollars for one day.
                        
                        An accidental death benefit of ten thousand dollars is included.
                        ```
                        
                        5. Thank you slide special rules:
                           - Must use layout: end
                           - Must include FirstEnroll logo
                           - Script should be a concise closing statement
                        
                        6. Image and layout rules:
                           - Look at descriptive filenames to match content
                           - Add page images in frontmatter: `image: img/pages/*.png`
                           - Only insert page images where content clearly matches
                           - If slide content matches an image subject, use layout: one-half-img
                           - If no matching image, use layout: default
                           - Plan tiers and limitations slides should always have images
                        
                        7. Logo rules:
                           - Add provider logos when their benefits are mentioned
                           - Wrap logos in the same v-click with related benefit text
                           - All logo paths must start with ./ (e.g., ./img/logos/provider_logo.png)
                           - Logos should be a small to medium size, set with Tailwinds
                        
                        8. Script formatting:
                           - Each point should be on its own line
                           - One empty line between each point
                           - First line introduces the section (before any v-click content)
                           - Points should align with slide v-clicks in order
                        
                        Return your response in this exact JSON format:
                        {
                            "needs_fixes": true/false,
                            "changes_made": [
                                "list of specific changes made"
                            ],
                            "slide": {
                                "header": "complete header block with transitions/layout/image?",
                                "content": "complete slide content with v-clicks in bulleted lists"
                            },
                            "script": {
                                "header": "---- Section Title ----",
                                "content": "complete script content with proper line spacing and alignment to v-clicks"
                            }
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"""Please validate and fix this section:
                        Title: {title}
                        Available images: {json.dumps(image_paths, indent=2)}
                        Slide Header: {matching_slide["header"]}
                        Slide Content: {matching_slide["content"]}
                        Script Header: {section["header"]}
                        Script Content: {section["content"]}
                        Plan tiers: {json.dumps(state.get("plan_tiers", {}), indent=2)}
                        """
                    }
                ]
                
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000,
                    response_format={ "type": "json_object" }
                )
                
                try:
                    fixes = json.loads(response.choices[0].message.content)
                    
                    if fixes.get("needs_fixes", False):
                        all_fixes.extend(fixes.get("changes_made", []))
                        
                        # Update the sections in state
                        if "slide" in fixes:
                            matching_slide["header"] = fixes["slide"].get("header", matching_slide["header"])
                            matching_slide["content"] = fixes["slide"].get("content", matching_slide["content"])
                        
                        if "script" in fixes:
                            section["header"] = fixes["script"].get("header", section["header"])
                            section["content"] = fixes["script"].get("content", section["content"])
                            
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing validation response for section {title}: {str(e)}")
        
        # Simple reassembly from state
        logger.info("\nReassembling content from state")
        
        # Sort sections by their original index
        sorted_slides = sorted(state["sections"]["slides"], key=lambda x: x["original_index"])
        sorted_script = sorted(state["sections"]["script"], key=lambda x: x["original_index"])
        
        # Build final content with proper spacing
        final_slides = []
        logger.info("\nProcessing slide sections:")
        for slide in sorted_slides:
            # Skip empty headers (these are the duplicates)
            if not slide['content'].strip():
                logger.info(f"  Skipping empty section: {slide['title']}")
                continue
                
            logger.info(f"  Including section: {slide['title']}")
            final_slides.append(f"{slide['header'].rstrip()}\n\n{slide['content'].strip()}")
        
        logger.info("\nProcessing script sections:")
        final_script = []
        for script in sorted_script:
            logger.info(f"  Including section: {script['title']}")
            final_script.append(f"{script['header'].strip()}\n\n{script['content'].strip()}")
        
        # Join all sections with double newlines
        final_slides_content = "\n\n".join(final_slides)
        final_script_content = "\n\n".join(final_script)
        
        # Save if changes were made
        if all_fixes:
            await save_content(slides_path, final_slides_content)
            await save_content(script_path, final_script_content)
            logger.info(f"Reassembled {len(final_slides)} slides and {len(final_script)} script sections")
            
        # Update state
        state["validation_result"] = {
            "needs_fixes": bool(all_fixes),
            "changes_made": all_fixes
        }
        
        return state
        
    except Exception as e:
        logger.error(f"Error in validate_and_fix: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "validation"
        }
        return state 