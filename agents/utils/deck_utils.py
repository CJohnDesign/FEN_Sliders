from pathlib import Path
import shutil
import os
from typing import Dict, Any, List, Optional, Union
import json

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
                
        # Copy PDF file from template if it exists
        template_pdf_dir = template_path / "img" / "pdfs"
        deck_pdf_dir = deck_path / "img" / "pdfs"
        pdf_files = list(template_pdf_dir.glob("*.pdf"))
        if pdf_files:
            # Copy the first PDF file found
            shutil.copy2(pdf_files[0], deck_pdf_dir / pdf_files[0].name)
            
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

def load_tables_data(deck_path: Union[str, Path]) -> Dict[str, List[Dict]]:
    """Load all table data for a deck.
    
    Args:
        deck_path: Path to the deck directory
        
    Returns:
        Dict containing:
        - manifest: The tables manifest data
        - tables: List of table data with contents
    """
    deck_path = Path(deck_path)
    tables_dir = deck_path / "ai" / "tables"
    manifest_path = tables_dir / "manifest.json"
    
    if not manifest_path.exists():
        return {"manifest": None, "tables": []}
        
    try:
        # Load manifest
        with open(manifest_path) as f:
            manifest = json.load(f)
            
        # Load each table's contents
        tables = []
        for table_info in manifest["tables"]:
            table_path = tables_dir / table_info["filename"]
            if table_path.exists():
                with open(table_path) as f:
                    tables.append({
                        "page": table_info["page"],
                        "title": table_info["title"],
                        "filename": table_info["filename"],
                        "headers": table_info["headers"],
                        "row_count": table_info["row_count"],
                        "data": f.read()
                    })
                    
        return {
            "manifest": manifest,
            "tables": tables
        }
        
    except Exception as e:
        print(f"Error loading tables: {str(e)}")
        return {"manifest": None, "tables": []}

def get_table_by_page(deck_path: Union[str, Path], page_number: int) -> Optional[Dict]:
    """Get table data for a specific page.
    
    Args:
        deck_path: Path to the deck directory
        page_number: The page number to get table data for
        
    Returns:
        Table data dict if found, None otherwise
    """
    tables_data = load_tables_data(deck_path)
    if not tables_data["tables"]:
        return None
        
    for table in tables_data["tables"]:
        if table["page"] == page_number:
            return table
            
    return None

def get_all_table_contents(deck_path: Union[str, Path]) -> str:
    """Get all table contents concatenated with headers.
    
    Args:
        deck_path: Path to the deck directory
        
    Returns:
        String containing all table data with headers
    """
    tables_data = load_tables_data(deck_path)
    if not tables_data["tables"]:
        return ""
        
    content = []
    for table in tables_data["tables"]:
        content.append(f"Table from page {table['page']} - {table['title']}:")
        content.append(table["data"])
        content.append("")  # Empty line between tables
        
    return "\n".join(content) 