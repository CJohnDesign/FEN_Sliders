"""Table extraction node for the builder agent."""
import os
import json
import logging
import base64
from typing import Dict
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

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

async def extract_tables(state: Dict) -> Dict:
    """Extract tables from pages marked as containing tables."""
    try:
        logger.info("Starting table extraction...")
        logger.info(f"State contains: {list(state.keys())}")
        
        if state.get("error_context"):
            logger.warning("Error context found in state, skipping table extraction")
            return state
            
        if not state.get("deck_info"):
            error_msg = "No deck info available"
            logger.error(error_msg)
            state["error_context"] = {
                "error": error_msg,
                "stage": "table_extraction"
            }
            return state

        deck_dir = Path(state["deck_info"]["path"])
        logger.info(f"Working with deck directory: {deck_dir}")

        tables_dir = deck_dir / "ai" / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created/verified tables directory at: {tables_dir}")

        summaries_path = deck_dir / "ai" / "summaries.json"
        if not summaries_path.exists():
            error_msg = "Summaries file not found"
            logger.error(error_msg)
            state["error_context"] = {
                "error": error_msg,
                "stage": "table_extraction"
            }
            return state
            
        with open(summaries_path, "r") as f:
            summaries = json.load(f)
        
        logger.info(f"Loaded {len(summaries)} summaries")
        pages_with_tables = [s for s in summaries if s.get("hasTable", False)]
        logger.info(f"Found {len(pages_with_tables)} pages marked with hasTable=true")

        chat = ChatOpenAI(
            model="gpt-4o",
            max_tokens=4096,
            temperature=0
        )
        logger.info("Initialized chat model")

        manifest = {"tables": []}
        
        for summary in pages_with_tables:
            logger.info(f"Processing table for page {summary['page']}")
            
            image_path = deck_dir / "img" / "pdfs" / f"page_{summary['page']}.png"
            if not image_path.exists():
                logger.error(f"Image file not found: {image_path}")
                continue
                
            try:
                image_data = encode_image(str(image_path))
                logger.info(f"Successfully encoded image: {image_path}")
                
                messages = [
                    HumanMessage(content=[
                        {
                            "type": "text",
                            "text": "Convert this table to CSV format. Return only the CSV text."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}",
                                "detail": "high"
                            }
                        }
                    ])
                ]
                
                logger.info(f"Sending request to model for page {summary['page']}")
                response = await chat.ainvoke(messages)
                csv_content = response.content.strip()
                
                if csv_content:
                    table_path = tables_dir / f"table_{summary['page']:03d}.tsv"
                    with open(table_path, "w") as f:
                        f.write(csv_content)
                    logger.info(f"Saved CSV content to {table_path}")
                    
                    manifest["tables"].append({
                        "page": summary["page"],
                        "path": str(table_path.relative_to(deck_dir))
                    })
                    
                    summary["table_path"] = str(table_path.relative_to(deck_dir))
                else:
                    logger.warning(f"No table content extracted for page {summary['page']}")
                    
            except Exception as e:
                logger.error(f"Failed to process table for page {summary['page']}: {str(e)}")
                continue

        manifest_path = tables_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Saved tables manifest to {manifest_path}")

        with open(summaries_path, "w") as f:
            json.dump(summaries, f, indent=2)
        logger.info("Updated summaries.json with table references")

        logger.info(f"Table extraction complete. Successfully processed {len(manifest['tables'])} tables")
        return state
        
    except Exception as e:
        logger.error(f"Failed to extract tables: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "table_extraction"
        }
        return state 