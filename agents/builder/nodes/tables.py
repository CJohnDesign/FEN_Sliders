"""Table extraction node for the builder agent."""
import os
import json
import logging
import base64
from typing import Dict
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..config.models import get_model_config
from langsmith.run_helpers import traceable

logger = logging.getLogger(__name__)

def encode_image(image_path: str) -> str:
    """Encode an image file to base64."""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            logger.info(f"Successfully encoded image: {image_path}")
            return encoded_string
    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {str(e)}")
        raise

@traceable(name="extract_tables")
async def extract_tables(state: Dict) -> Dict:
    """Extract tables from slides and save as TSV files"""
    try:
        logger.info("Starting table extraction...")
        
        # Initialize tables data structure
        tables_data = {
            "tables": []
        }
        
        deck_dir = Path(state["deck_info"]["path"])
        img_dir = deck_dir / "img" / "pages"
        tables_dir = deck_dir / "ai" / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
        
        # Get list of PNG files
        png_files = sorted([f for f in os.listdir(img_dir) if f.endswith('.png')])
        
        # Initialize model with config
        model_config = get_model_config()
        model = ChatOpenAI(**model_config)
        
        for i, png_file in enumerate(png_files, 1):
            logger.info(f"Processing table for page {i}")
            img_path = img_dir / png_file
            
            try:
                # Encode image
                base64_image = encode_image(str(img_path))
                logger.info(f"Successfully encoded image for page {i}")
                
                # Create messages for model
                messages = [
                    SystemMessage(content="""You are an expert at extracting tables from images.
                    If you find a table in the image, extract it and return it in TSV format.
                    If there is no table, return "NO_TABLE".
                    Only return the TSV content or NO_TABLE - no other text."""),
                    HumanMessage(content=[
                        {
                            "type": "text", 
                            "text": "Extract any tables from this image in TSV format."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ])
                ]
                
                # Get model response
                logger.info(f"Sending request to model for page {i}")
                response = await model.ainvoke(messages)
                logger.info(f"Received response from model for page {i}")
                
                content = response.content.strip()
                
                # Skip if no table found
                if content == "NO_TABLE":
                    continue
                    
                # Save table content
                table_filename = f"table_{i:03d}.tsv"
                table_path = tables_dir / table_filename
                with open(table_path, "w") as f:
                    f.write(content)
                logger.info(f"Saved TSV content to {table_path}")
                
                # Add to tables data
                tables_data["tables"].append({
                    "page": i,
                    "filename": table_filename,
                    "path": str(table_path.relative_to(deck_dir))
                })
                logger.info(f"Added table path to summary for page {i}")
                
            except Exception as e:
                logger.error(f"Error processing page {i}: {str(e)}")
                logger.error("Full error context:", exc_info=True)
                continue
        
        # Save tables manifest
        manifest_path = tables_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(tables_data, f, indent=2)
        logger.info("Saved tables manifest to decks/FEN_ADP/ai/tables/manifest.json")
        
        # Update state
        state["tables_data"] = tables_data
        logger.info(f"Table extraction complete. Successfully processed {len(tables_data['tables'])} tables")
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to extract tables: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        logger.error(f"State contents: {list(state.keys())}")
        logger.info("Continuing despite table extraction failure")
        return state 