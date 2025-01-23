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
        pages_with_tables = [s for s in summaries if s.get("tableDetails", {}).get("hasBenefitsTable", False)]
        logger.info(f"Found {len(pages_with_tables)} pages marked with hasBenefitsTable=true")

        chat = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8000,
            temperature=0
        )
        logger.info("Initialized chat model with gpt-4o")

        manifest = {"tables": []}
        
        for summary in pages_with_tables:
            try:
                logger.info(f"Processing table for page {summary['page']}")
                
                image_path = deck_dir / "img" / "pages" / f"page_{summary['page']}.png"
                if not image_path.exists():
                    logger.error(f"Image file not found: {image_path}")
                    continue

                # Get base64 of image
                image_base64 = encode_image(str(image_path))
                logger.info(f"Successfully encoded image for page {summary['page']}")
                
                messages = [
                    HumanMessage(content=[
                        {
                            "type": "text",
                            "text": """Here is an image of a benefits table. Return in a clean tab-separated (TSV) format, using tabs (\t) as separators between columns. Return only the TSV text without anything else.

Be very careful to not include any other text in the output and ensure it is a true representation of the information in the table."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ])
                ]

                logger.info(f"Sending request to model for page {summary['page']}")
                response = await chat.ainvoke(messages)
                logger.info(f"Received response from model for page {summary['page']}")
                tsv_content = response.content
                
                if tsv_content:
                    table_path = tables_dir / f"table_{summary['page']:03d}.tsv"
                    with open(table_path, "w") as f:
                        f.write(tsv_content)
                    logger.info(f"Saved TSV content to {table_path}")
                    
                    manifest["tables"].append({
                        "page": summary["page"],
                        "path": str(table_path.relative_to(deck_dir))
                    })
                    
                    summary["table_path"] = str(table_path.relative_to(deck_dir))
                    logger.info(f"Added table path to summary for page {summary['page']}")
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

        # Even if some tables fail, continue with the process
        logger.info(f"Table extraction complete. Successfully processed {len(manifest['tables'])} tables")
        logger.info(f"Final state keys: {list(state.keys())}")
        logger.info(f"Tables data: {json.dumps(tables_data, indent=2)}")
        logger.info(f"State error context: {state.get('error_context')}")
        return state
        
    except Exception as e:
        logger.error(f"Failed to extract tables: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        logger.error(f"State contents: {list(state.keys())}")
        # Don't stop the process on table extraction failure
        logger.info("Continuing despite table extraction failure")
        return state 