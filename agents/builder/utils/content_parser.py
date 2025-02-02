"""Content parsing utilities for the builder agent."""
from typing import Dict, List, TypedDict
import re

class Section(TypedDict):
    header: str
    content: str

def parse_script_sections(script_content: str) -> List[Section]:
    """Parse script content into sections based on ---- Section ---- markers."""
    sections = []
    current_section = None
    current_content = []
    
    for line in script_content.split('\n'):
        # Check for section header
        if line.startswith('----') and line.endswith('----'):
            # Save previous section if exists
            if current_section:
                sections.append({
                    'header': current_section,
                    'content': '\n'.join(current_content).strip()
                })
            # Start new section
            current_section = line.strip('-').strip()
            current_content = []
        else:
            if current_section and line.strip():
                current_content.append(line)
    
    # Add final section
    if current_section:
        sections.append({
            'header': current_section,
            'content': '\n'.join(current_content).strip()
        })
    
    return sections

def parse_slides_sections(slides_content: str) -> List[Section]:
    """Parse slides content into sections based on # Section markers."""
    sections = []
    current_section = None
    current_content = []
    
    for line in slides_content.split('\n'):
        # Check for section header (h1 or h2)
        if line.startswith('# ') or line.startswith('## '):
            # Save previous section if exists
            if current_section:
                sections.append({
                    'header': current_section,
                    'content': '\n'.join(current_content).strip()
                })
            # Start new section
            current_section = line.lstrip('#').strip()
            current_content = []
        else:
            if current_section:
                current_content.append(line)
    
    # Add final section
    if current_section:
        sections.append({
            'header': current_section,
            'content': '\n'.join(current_content).strip()
        })
    
    return sections

def update_state_with_content(state: Dict) -> Dict:
    """Update state with parsed sections from script and slides."""
    # Parse script sections if script exists
    if state.get('script'):
        state['script_sections'] = parse_script_sections(state['script'])
    
    # Parse slides sections if slides exist
    if state.get('slides'):
        state['slides_sections'] = parse_slides_sections(state['slides'])
    
    return state 