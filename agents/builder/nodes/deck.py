"""Deck creation and structure management."""
import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict
from ..utils.retry_utils import retry_with_exponential_backoff
from ..utils.logging_utils import setup_logger

# Set up logger
logger = setup_logger(__name__)

@retry_with_exponential_backoff()
def create_deck_structure(state: Dict) -> Dict:
    """Create the initial deck structure and return state."""
    try:
        # Get parameters from state
        metadata = state.get("metadata", {})
        deck_id = metadata.get("deck_id")
        title = metadata.get("title")
        template = metadata.get("template", "FEN_TEMPLATE")
        
        if not deck_id or not title:
            raise ValueError("Missing required metadata: deck_id or title")
            
        logger.info(f"Creating deck structure for {deck_id}")
        
        # Create base directory structure
        deck_path = Path("decks") / deck_id
        template_path = Path("decks") / template
        
        # Create the deck directory if it doesn't exist
        deck_path.mkdir(parents=True, exist_ok=True)
        
        # Define directories to create and copy
        directories = [
            "ai",
            "ai/tables",
            "audio",
            "audio/oai",
            "img",
            "img/logos",
            "img/pdfs",
            "img/pages",
            "dist"
        ]
        
        # Create all required directories
        for dir_path in directories:
            (deck_path / dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {deck_path / dir_path}")
        
        # Copy template files and directories
        def copy_directory_contents(src_dir: Path, dst_dir: Path):
            """Copy all contents from source to destination directory."""
            if not src_dir.exists():
                logger.warning(f"Source directory does not exist: {src_dir}")
                return
                
            for item in src_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, dst_dir / item.name)
                    logger.info(f"Copied file: {item.name}")
                elif item.is_dir():
                    new_dst = dst_dir / item.name
                    new_dst.mkdir(exist_ok=True)
                    copy_directory_contents(item, new_dst)
        
        # Copy template structure
        template_dirs = {
            "img/logos": deck_path / "img" / "logos",
            "img/pdfs": deck_path / "img" / "pdfs",
            "img/pages": deck_path / "img" / "pages",
            "audio": deck_path / "audio"
        }
        
        for src_path, dst_path in template_dirs.items():
            src_full_path = template_path / src_path
            copy_directory_contents(src_full_path, dst_path)
        
        # Copy slides.md if it exists
        template_slides = template_path / "slides.md"
        if template_slides.exists():
            shutil.copy2(template_slides, deck_path / "slides.md")
            logger.info("Copied slides.md template")
        
        # Create initial metadata
        metadata.update({
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        })
        
        # Save metadata
        with open(deck_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Successfully created deck structure at {deck_path}")
        
        # Update state
        state["deck_info"] = {
            "path": str(deck_path),
            "metadata": metadata
        }
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to create deck structure: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "create_deck_structure"
        }
        return state 