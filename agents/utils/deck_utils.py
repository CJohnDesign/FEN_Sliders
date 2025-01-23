from pathlib import Path
import shutil
import os
from typing import Dict, Any, List, Optional, Union
import json
import logging

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('builder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def create_structure(deck_id: str, title: str, template: str = "FEN_TEMPLATE") -> Dict[str, Any]:
    """Creates the basic deck structure based on template"""
    logger.info(f"Creating deck structure - ID: {deck_id}, Title: {title}, Template: {template}")
    
    try:
        # Construct paths
        base_dir = Path(__file__).parent.parent.parent
        deck_path = base_dir / "decks" / deck_id
        template_path = base_dir / "decks" / template
        
        logger.info(f"Base directory: {base_dir}")
        logger.info(f"Template directory: {template_path}")
        logger.info(f"Target deck directory: {deck_path}")
        
        # Check if template exists
        if not template_path.exists():
            error_msg = f"Template '{template}' not found in decks directory"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        # Create deck directory if it doesn't exist
        logger.info("Creating deck directory structure...")
        deck_path.mkdir(parents=True, exist_ok=True)
        
        # Create required subdirectories
        subdirs = ['ai', 'audio', 'img/logos', 'img/pdfs', 'dist']
        for subdir in subdirs:
            (deck_path / subdir).mkdir(parents=True, exist_ok=True)
            
        # Copy template files
        template_files = [
            'slides.md',
            '.gitkeep'
        ]
        
        for file in template_files:
            src = template_path / file
            if src.exists():
                dst = deck_path / file
                shutil.copy2(src, dst)
                logger.info(f"Copied template file: {file} to {dst}")
                
        # Copy PDF from template's img/pdfs directory
        template_pdf = template_path / "img" / "pdfs" / "US_Fire.pdf"
        if template_pdf.exists():
            dst = deck_path / "img" / "pdfs" / "US_Fire.pdf"
            shutil.copy2(template_pdf, dst)
            logger.info(f"Copied PDF file from template: {template_pdf} to {dst}")
                
        # Create deck info
        deck_info = {
            "path": str(deck_path),
            "template": template,
            "title": title,
            "subdirs": {
                subdir: str(deck_path / subdir)
                for subdir in subdirs
            }
        }
        
        # Save deck info
        with open(deck_path / "deck_info.json", "w") as f:
            json.dump(deck_info, f, indent=2)
            
        logger.info("Successfully created deck structure")
        return deck_info
        
    except Exception as e:
        logger.error(f"Error creating deck structure: {str(e)}")
        raise

def load_tables_data(deck_dir: Path) -> dict:
    """Load table data from the deck directory"""
    try:
        # Load summaries to check which pages have tables
        summaries_path = deck_dir / "ai" / "summaries.json"
        if not summaries_path.exists():
            return {"tables": []}
            
        with open(summaries_path) as f:
            summaries = json.load(f)
            
        # Get pages with tables
        pages_with_tables = [summary["page"] for summary in summaries if summary.get("tableDetails", {}).get("hasBenefitsTable", False)]
        
        if not pages_with_tables:
            return {"tables": []}
            
        # Load tables from TSV files
        tables_dir = deck_dir / "ai" / "tables"
        if not tables_dir.exists():
            return {"tables": []}
            
        tables = []
        for page in pages_with_tables:
            table_file = tables_dir / f"table_{page:03d}.tsv"
            if table_file.exists():
                with open(table_file) as f:
                    table_data = f.read()
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
    try:
        # Convert to Path if string
        if isinstance(deck_path, str):
            deck_path = Path(deck_path)
            
        # Check for table file directly
        table_file = deck_path / "ai" / "tables" / f"table_{page_number:03d}.tsv"
        if not table_file.exists():
            return None
            
        with open(table_file) as f:
            table_data = f.read()
            
        return {
            "page": page_number,
            "data": table_data
        }
        
    except Exception as e:
        print(f"Error loading table for page {page_number}: {str(e)}")
        return None

def get_all_table_contents(deck_path: Union[str, Path]) -> str:
    """Get all table contents concatenated with headers.
    
    Args:
        deck_path: Path to the deck directory
        
    Returns:
        String containing all table data with headers
    """
    try:
        # Convert to Path if string
        if isinstance(deck_path, str):
            deck_path = Path(deck_path)
            
        tables_data = load_tables_data(deck_path)
        if not tables_data["tables"]:
            return ""
            
        content = []
        for table in tables_data["tables"]:
            content.append(f"Table from page {table['page']}:")
            content.append(table["data"])
            content.append("")  # Empty line between tables
            
        return "\n".join(content)
        
    except Exception as e:
        print(f"Error getting table contents: {str(e)}")
        return "" 