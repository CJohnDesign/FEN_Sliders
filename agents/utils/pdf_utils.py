from pathlib import Path
from typing import Dict, Any
from pdf2image import convert_from_path
import shutil
import logging

# Set up logging
logger = logging.getLogger(__name__)

async def convert_pdf_to_images(deck_id: str, deck_path: str) -> Dict[str, Any]:
    """Convert PDF to JPG images.
    
    Args:
        deck_id: The ID of the deck
        deck_path: Path to the deck directory
        
    Returns:
        Dict containing status and results
    """
    try:
        # Construct paths
        deck_dir = Path(deck_path)
        pdf_dir = deck_dir / "img" / "pdfs"
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            return {
                "status": "error",
                "error": "No PDF files found in img/pdfs directory"
            }
            
        # Use the first PDF found
        pdf_path = pdf_files[0]
        output_dir = deck_dir / "img" / "pages"
        
        logger.info(f"Converting PDF: {pdf_path}")
        logger.info(f"Output directory: {output_dir}")
        
        # Clean up existing images
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert PDF to images with high quality settings
        images = convert_from_path(
            str(pdf_path),
            dpi=300,  # High resolution
            fmt="jpeg",
            output_folder=str(output_dir),
            output_file=f"slide_",  # Will create slide_1.jpg, slide_2.jpg, etc.
            paths_only=True,  # Return paths instead of PIL images to save memory
            thread_count=4  # Use multiple threads for faster conversion
        )
        
        # Verify images were created
        created_images = list(output_dir.glob("*.jpg"))
        if not created_images:
            return {
                "status": "error",
                "error": "No images were created during conversion"
            }
            
        logger.info(f"Successfully converted {len(created_images)} pages")
        
        return {
            "status": "success",
            "page_count": len(created_images),
            "output_dir": str(output_dir)
        }
        
    except Exception as e:
        logger.error(f"PDF conversion failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        } 