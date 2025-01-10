from pathlib import Path
from langchain_core.messages import AIMessage
from pdf2image import convert_from_path
from ..state import BuilderState

async def wait_for_pdf(state: BuilderState) -> BuilderState:
    """Pauses the workflow to wait for PDF upload"""
    # Add a message to the state indicating we're waiting
    state["messages"].append(
        AIMessage(content="Please upload the PDF file for the deck. Once uploaded, the process will continue.")
    )
    
    # Set a flag in the state to indicate we're waiting for input
    state["awaiting_input"] = "pdf_upload"
    
    return state

async def process_imgs(state: BuilderState) -> BuilderState:
    """Process the images and create structured summaries"""
    try:
        # Skip if there was an error in previous steps
        if state.get("error_context"):
            return state
            
        # Get image directory path
        if not state.get("deck_info"):
            state["error_context"] = {
                "error": "No deck info available",
                "stage": "image_processing"
            }
            return state
            
        # Get paths
        deck_dir = Path(state["deck_info"]["path"])
        img_dir = deck_dir / "img" / "pages"
        
        # Clean up existing images
        if img_dir.exists():
            existing_files = list(img_dir.glob("*.jpg"))
            if existing_files:
                for file in existing_files:
                    file.unlink()
            
        # Convert PDF to images
        pdf_dir = deck_dir / "img" / "pdfs"
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            state["error_context"] = {
                "error": "No PDF files found",
                "stage": "image_processing"
            }
            return state
            
        # Use the first PDF found
        pdf_path = pdf_files[0]
        
        # Ensure output directory exists
        img_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert PDF to images
        images = convert_from_path(str(pdf_path))
        
        # Save each page as JPG with consistent naming
        for i, image in enumerate(images, start=1):
            output_path = img_dir / f"slide_{i:03d}.jpg"
            image.save(output_path, "JPEG")
            
        # Update state with image info
        state["pdf_info"] = {
            "page_count": len(images),
            "output_dir": str(img_dir)
        }
        
        # Add success message
        state["messages"].append(
            AIMessage(content=f"Successfully converted PDF to {len(images)} images.")
        )
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "image_processing"
        }
        return state 