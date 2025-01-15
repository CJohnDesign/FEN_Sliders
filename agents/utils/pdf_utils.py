from pathlib import Path
from typing import Dict, Any
from pdf2image import convert_from_path
import shutil

async def convert_pdf_to_images(deck_id: str, deck_path: str) -> Dict[str, Any]:
    """Convert PDF to JPG images"""
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
        
        # Clean up existing images
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert PDF to images
        images = convert_from_path(str(pdf_path))
        
        # Save each page as JPG with consistent naming
        for i, image in enumerate(images, start=1):
            image.save(output_dir / f"slide_{i:03d}.jpg", "JPEG")
            
        return {
            "status": "success",
            "page_count": len(images),
            "output_dir": str(output_dir)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        } 