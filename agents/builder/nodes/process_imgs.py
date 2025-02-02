"""PDF processing node for the builder agent."""
import os
import logging
from typing import List, Dict, Any
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from ..state import BuilderState
from ..utils.logging_utils import setup_logger, log_async_step, log_step_result
from langchain_core.messages import AIMessage

# Set up logger
logger = setup_logger(__name__)

async def wait_for_pdf(state: BuilderState) -> BuilderState:
    """Pauses the workflow to wait for PDF upload"""
    logger.info("Waiting for PDF upload...")
    state.messages.append(
        AIMessage(content="Please upload the PDF file for the deck. Once uploaded, the process will continue.")
    )
    state.awaiting_input = "pdf_upload"
    return state

@log_async_step(logger)
async def process_imgs(state: BuilderState) -> BuilderState:
    """Process PDF file and convert pages to images."""
    try:
        logger.info(f"Starting process_imgs...")
        logger.info(f"State contains: {[key for key in vars(state).keys()]}")

        # Get deck directory
        if not state.deck_info or "path" not in state.deck_info:
            log_step_result(
                logger,
                "pdf_processing",
                False,
                "No deck directory found in state"
            )
            state.error_context = {
                "error": "No deck directory found in state",
                "stage": "pdf_processing"
            }
            return state
            
        deck_dir = state.deck_info["path"]
        logger.info(f"Working with deck directory: {deck_dir}")
        
        # Find PDF file in root directory first
        deck_path = Path(deck_dir)
        pdf_files = list(deck_path.glob("*.pdf"))
        
        # If no PDFs in root, check img/pdfs directory
        if not pdf_files:
            pdf_dir = deck_path / "img" / "pdfs"
            if not pdf_dir.exists():
                log_step_result(
                    logger,
                    "pdf_processing",
                    False,
                    f"PDF directory not found at: {pdf_dir}"
                )
                state.error_context = {
                    "error": f"PDF directory not found at: {pdf_dir}",
                    "stage": "pdf_processing"
                }
                return state
                
            pdf_files = list(pdf_dir.glob("*.pdf"))
            
        if not pdf_files:
            log_step_result(
                logger,
                "pdf_processing",
                False,
                "No PDF files found"
            )
            state.error_context = {
                "error": "No PDF files found",
                "stage": "pdf_processing"
            }
            return state
            
        # Use the first PDF file found
        pdf_path = str(pdf_files[0])
        logger.info(f"Found PDF file: {pdf_path}")
        
        # Create img/pdfs directory if it doesn't exist
        pdf_dir = deck_path / "img" / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Move PDF to img/pdfs if it's in root
        if pdf_files[0].parent == deck_path:
            new_pdf_path = pdf_dir / pdf_files[0].name
            pdf_files[0].rename(new_pdf_path)
            pdf_path = str(new_pdf_path)
            logger.info(f"Moved PDF to: {pdf_path}")
        
        # Create img/pages directory for extracted images
        pages_dir = deck_path / "img" / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert PDF pages to images
        logger.info("Converting PDF pages to images...")
        images = convert_from_path(pdf_path)
        
        # Save images to pages directory
        page_paths = []
        for i, image in enumerate(images):
            image_path = str(pages_dir / f"page_{i+1}.png")
            image.save(image_path, "PNG")
            page_paths.append(image_path)
            
        logger.info(f"Converted {len(page_paths)} pages to images")
        
        # Update state
        state.pdf_path = pdf_path
        state.pdf_info = {
            "num_pages": len(page_paths),
            "page_paths": page_paths,
            "output_dir": str(pages_dir)
        }
        
        log_step_result(
            logger,
            "pdf_processing",
            True,
            f"Successfully processed PDF with {len(page_paths)} pages"
        )
        return state
        
    except Exception as e:
        log_step_result(
            logger,
            "pdf_processing",
            False,
            f"Failed to process PDF: {str(e)}"
        )
        state.error_context = {
            "error": str(e),
            "stage": "pdf_processing"
        }
        return state 