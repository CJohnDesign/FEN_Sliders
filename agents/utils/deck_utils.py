from pathlib import Path
import shutil
import os
from typing import Dict, Any

async def create_structure(deck_id: str, template: str = "FEN_TEMPLATE") -> Dict[str, Any]:
    """Creates the basic deck structure based on template"""
    try:
        # Construct paths
        base_dir = Path(__file__).parent.parent.parent
        deck_path = base_dir / "decks" / f"FEN_{deck_id}"
        template_path = base_dir / "decks" / template
        
        # Check if template exists
        if not template_path.exists():
            return {
                "status": "error",
                "error": f"Template '{template}' not found in decks directory"
            }
            
        # Create deck directory if it doesn't exist
        deck_path.mkdir(parents=True, exist_ok=True)
        
        # Copy template structure
        for item in template_path.iterdir():
            if item.is_dir():
                shutil.copytree(item, deck_path / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, deck_path / item.name)
            
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