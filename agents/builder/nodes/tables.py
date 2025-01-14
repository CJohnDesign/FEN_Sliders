import json
import base64
import logging
from pathlib import Path
from ...utils import llm_utils
from ..state import BuilderState

async def extract_tables(state: BuilderState) -> BuilderState:
    """Extract tables from slides and add them as CSV to summaries"""
    try:
        if state.get("error_context"):
            return state
            
        deck_path = Path(state["deck_info"]["path"])
        summaries_path = deck_path / "ai" / "summaries.json"
        
        # Read summaries
        with open(summaries_path) as f:
            summaries = json.load(f)
            
        # Find slides with tables
        table_slides = [s for s in summaries if s.get("hasTable", False)]
        
        if not table_slides:
            return state
            
        # Get non-vision LLM
        llm = llm_utils.get_llm(model="gpt-4o", vision=False)
        
        # Process each table slide
        for slide in table_slides:
            page_num = slide["page"]
            img_path = deck_path / "img" / "pages" / f"slide_{page_num:03d}.jpg"
            
            if not img_path.exists():
                continue
                
            # Encode image
            try:
                with open(img_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            except Exception as e:
                logging.error(f"Failed to encode image for page {page_num}: {str(e)}")
                continue
            
            messages = [
                {
                    "role": "system",
                    "content": """You are a table extraction expert. Your task is to look at an image and extract any tables you find into CSV format.
                    Return ONLY the CSV content, with no additional text or explanation.
                    Use commas as delimiters and newlines between rows.
                    If there are multiple tables, separate them with three newlines."""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all tables from this image and return them in CSV format only."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            try:
                response = await llm.ainvoke(messages)
                if isinstance(response, dict):
                    content = response.get("content", "")
                else:
                    content = str(response)
                
                # Find the matching summary in the original list and update it
                for summary in summaries:
                    if summary["page"] == page_num:
                        summary["csv"] = content
                        break
                
            except Exception as e:
                logging.error(f"Failed to extract table from slide {page_num}: {str(e)}")
                continue
                
        # Save updated summaries
        with open(summaries_path, "w") as f:
            json.dump(summaries, f, indent=2)
            
        # Update state
        state["page_summaries"] = summaries
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "table_extraction"
        }
        return state 