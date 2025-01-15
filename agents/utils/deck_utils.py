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

def load_tables_data(deck_dir: Path) -> dict:
    """Load table data from the deck directory"""
    try:
        # Load summaries to check which pages have tables
        summaries_path = deck_dir / "ai" / "summaries.json"
        if not summaries_path.exists():
            return {"tables": []}
            
        with open(summaries_path) as f:
            summaries = json.load(f)
            
        # Get pages that have tables
        pages_with_tables = [summary["page"] for summary in summaries if summary.get("hasTable", False)]
        
        if not pages_with_tables:
            return {"tables": []}
            
        tables = []
        for page in pages_with_tables:
            table_data = get_table_by_page(deck_dir, page)
            if table_data:
                tables.append({
                    "page": page,
                    "data": table_data
                })
                
        return {"tables": tables}
        
    except Exception as e:
        print(f"Error loading tables: {str(e)}")
        return {"tables": []}

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