"""Deck creation and structure management."""
import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from agents.builder.utils.retry_utils import retry_with_exponential_backoff
from ..utils.logging_utils import setup_logger

from agents.builder.state import BuilderState

# Set up logger
logger = setup_logger(__name__)

@retry_with_exponential_backoff()
def create_deck_structure(state: BuilderState) -> BuilderState:
    """Create the initial deck structure."""
    try:
        metadata = state.metadata
        deck_id = metadata.deck_id
        template = metadata.template

        # Get paths
        deck_dir = Path("decks") / deck_id
        template_dir = Path("decks") / template

        # Create directories
        logger.info(f"Creating deck structure for {deck_id}")
        
        # Create main directories
        dirs = [
            deck_dir / "ai" / "tables",
            deck_dir / "audio" / "oai",
            deck_dir / "img" / "logos",
            deck_dir / "img" / "pdfs",
            deck_dir / "img" / "pages",
            deck_dir / "dist"
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")

        # Copy template files
        def copy_directory_contents(src_dir: Path, dst_dir: Path):
            """Copy all files from source to destination directory."""
            if not src_dir.exists():
                logger.warning(f"Source directory does not exist: {src_dir}")
                return
            
            for item in src_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, dst_dir)
                    logger.info(f"Copied file: {item.name}")

        # Copy logo files
        logger.info("Copying logos from template...")
        copy_directory_contents(template_dir / "img" / "logos", deck_dir / "img" / "logos")

        # Copy PDF files
        logger.info("Copying PDFs from template...")
        copy_directory_contents(template_dir / "img" / "pdfs", deck_dir / "img" / "pdfs")

        # Copy audio files
        logger.info("Copying audio files from template...")
        copy_directory_contents(template_dir / "audio", deck_dir / "audio")

        # Copy slides template
        slides_template = template_dir / "slides.md"
        if slides_template.exists():
            shutil.copy2(slides_template, deck_dir)
            logger.info("Copied slides.md template")
        else:
            logger.warning("No slides.md template found in template directory")

        # Update state with deck info
        state.deck_info = {
            "path": str(deck_dir),
            "template": template
        }

        logger.info(f"Successfully created deck structure at {deck_dir}")
        return state

    except Exception as e:
        logger.error(f"Failed to create deck structure: {str(e)}")
        state.error_context = {
            "error": str(e),
            "stage": "create_deck",
            "details": "Failed to create initial deck structure"
        }
        raise e 