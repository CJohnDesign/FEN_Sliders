from pathlib import Path
import shutil
import os
from typing import Dict, Any

async def create_structure(deck_id: str, template: str = "FEN_TEMPLATE") -> Dict[str, Any]:
    """Creates the basic deck structure based on template"""
    try:
        # Construct paths
        base_dir = Path(__file__).parent.parent.parent
        deck_path = base_dir / "decks" / deck_id
        template_path = base_dir / "decks" / template
        
        # Check if template exists
        if not template_path.exists():
            return {
                "status": "error",
                "error": f"Template '{template}' not found in decks directory"
            }
            
        # Create deck directory if it doesn't exist
        deck_path.mkdir(parents=True, exist_ok=True)
        
        # Create required subdirectories
        subdirs = ['ai', 'audio', 'img/logos', 'img/pdfs', 'dist']
        for subdir in subdirs:
            (deck_path / subdir).mkdir(parents=True, exist_ok=True)
            
        # Copy template files
        template_files = [
            'slides.md',
            'audio/audio_config.json',
            'audio/audio_script.md'
        ]
        
        for file in template_files:
            src = template_path / file
            dst = deck_path / file
            if src.exists():
                # Create parent directory if needed
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            
        return {
            "status": "success",
            "deck_path": str(deck_path),
            "template_used": template
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        } 