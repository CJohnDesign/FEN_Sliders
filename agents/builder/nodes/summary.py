import asyncio
import json
import base64
import logging
import signal
from pathlib import Path
from langchain_core.messages import AIMessage
from ...utils import llm_utils
from ..state import BuilderState
from ...utils.llm_utils import get_completion
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    filename='builder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def encode_image(image_path):
    """Convert an image file to base64 encoding"""
    try:
        with open(image_path, "rb") as image_file:
            # Don't log or print the base64 data
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logging.error(f"Error encoding image {image_path}: {str(e)}")
        raise

async def generate_page_summaries(state: BuilderState) -> BuilderState:
    """Generate summaries for each page and save to JSON"""
    try:
        if state.get("error_context"):
            return state
            
        if not state.get("pdf_info"):
            state["error_context"] = {
                "error": "No PDF info available",
                "stage": "summary_generation"
            }
            return state
            
        # Get vision-capable LLM
        llm = llm_utils.get_llm(vision=True)
        
        # Initialize summaries dict
        state["page_summaries"] = {}
        
        # Create ai directory if it doesn't exist
        ai_dir = Path(state["deck_info"]["path"]) / "ai"
        ai_dir.mkdir(exist_ok=True)
        
        # Get image paths
        output_dir = Path(state["pdf_info"]["output_dir"])
        image_files = sorted(output_dir.glob("slide_*.jpg"))
        
        # Process images in chunks of 3 with retries
        chunk_size = 3
        max_retries = 3
        delay_between_chunks = 2  # seconds
        
        summaries = []
        
        try:
            for chunk_start in range(0, len(image_files), chunk_size):
                chunk_end = min(chunk_start + chunk_size, len(image_files))
                chunk = image_files[chunk_start:chunk_end]
                
                for img_path in chunk:
                    page_num = int(img_path.stem.split('_')[1])
                    logging.info(f"Processing page {page_num}")
                    
                    # Encode image to base64 without printing
                    try:
                        base64_image = encode_image(img_path)
                    except Exception as e:
                        logging.error(f"Failed to encode image for page {page_num}: {str(e)}")
                        continue
                    
                    for retry in range(max_retries):
                        try:
                            messages = [
                                {
                                    "role": "system",
                                    "content": """You are an expert presentation analyst.
                                    Your task is to analyze a presentation slide and provide:
                                    1. A concise title that captures the main topic
                                    2. A detailed summary of the content
                                    3. A boolean `hasTable` indicating if the slide contains a table. return true if it does, false otherwise.

                                    Return `title`, `summary`, and `hasTable` in a JSON object.
                                    """
                                },
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"This is slide {page_num} of {state['pdf_info']['page_count']}. Please analyze it and provide a `title`, `summary`, and `hasTable` in JSON format."
                                        },
                                        {
                                            "type": "image_url",
                                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    ]
                                }
                            ]
                            
                            response = await llm(messages)
                            
                            try:
                                # The response is already a dictionary with 'role' and 'content'
                                content = response.get('content', {})
                                if not isinstance(content, dict):
                                    raise ValueError("Expected content to be a dictionary")
                                    
                                summaries.append({
                                    "page": page_num,
                                    "title": content.get("title", "Error: No Title"),
                                    "summary": content.get("summary", "Error: No Summary"),
                                    "hasTable": content.get("hasTable", False)
                                })
                                logging.info(f"Successfully processed page {page_num}")
                                break
                            except (json.JSONDecodeError, AttributeError) as e:
                                if retry == max_retries - 1:
                                    logging.error(f"Failed to parse JSON for page {page_num}: {str(e)}")
                                    summaries.append({
                                        "page": page_num,
                                        "title": "Error: Could not parse response",
                                        "summary": "Error processing page"
                                    })
                                    
                        except Exception as e:
                            error_msg = str(e)
                            if "invalid_api_key" in error_msg:
                                error_msg = "Invalid API key"
                            
                            if "overloaded" in error_msg.lower() and retry < max_retries - 1:
                                await asyncio.sleep(2 ** retry)
                                continue
                            elif retry == max_retries - 1:
                                logging.error(f"Failed to process page {page_num}: {error_msg}")
                                summaries.append({
                                    "page": page_num,
                                    "title": "Error",
                                    "summary": f"Failed to generate summary: {error_msg}"
                                })
                                break
                
                if chunk_end < len(image_files):
                    await asyncio.sleep(delay_between_chunks)
                    
        except asyncio.CancelledError:
            logging.info("Process interrupted by user")
            if summaries:
                logging.info(f"Saving {len(summaries)} summaries processed so far...")
            else:
                raise
            
        # Save summaries to file
        if summaries:
            summaries_file = ai_dir / "summaries.json"
            with open(summaries_file, "w") as f:
                json.dump(summaries, f, indent=2)
                
            # Update state with summaries
            state["page_summaries"] = summaries
            
        return state
                                    
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "summary_generation"
        }
        return state 

async def process_summaries(state: Dict[str, Any]) -> Dict[str, Any]:
    """Process summaries using script and slides template to generate markdown content"""
    
    deck_path = Path(state["deck_info"]["path"])
    summaries_path = deck_path / "ai" / "summaries.json"
    script_path = deck_path / "audio" / "audio_script.md"
    slides_path = deck_path / "slides.md"
    
    try:
        # Read existing files as raw text
        with open(summaries_path) as f:
            summaries_text = f.read()
        with open(script_path) as f:
            script_text = f.read()
        with open(slides_path) as f:
            slides_text = f.read()
            
        # Build the prompt with raw text content
        prompt = f"""You will be provided with the current summaries for educational content, along with script and slides templates.
Your task is to generate a presentation outline in a markdown file that presents this content in an organized, educational format.

The content should be structured with:

```
## 1. Core Plan Elements
- **Introduction & Overview**
  - Plan purpose and scope
  - Association membership (BWA, NCE, etc.)
  - Basic coverage framework

## 2. Common Service Features
- **Telehealth Services**
- **Preventive Care & Wellness**
- **Advocacy & Support**

## 3. Cost Management Tools
- **Medical Bill Management**

## 4. Plan Tiers

### Plans 1 (1/2)
- Benefits details list

### Plans 1 (2/2)
- Benefits details list

### Plans 2 (1/2)
- Benefits details list

### Plans 2 (2/2)
- Benefits details list

### Plans 3 (1/2)
- Benefits details list

### Plans 3 (2/2)
- Benefits details list

<!-- create as few or as many as needed -->

## 5. Administrative Details
- **Limitations & Definitions**
- **Required Disclosures**

## 6. Key Takeaways
- Plan comparison highlights
- Important reminders
```

Current summaries - use the information in these to generate the content:
{summaries_text}

Here are the slides that will be used to generate the content:
Notice their structure and how they are formatted. I want to keep this as close as possible.

Script template - maintain the header format:
{script_text}

Slides template - in this file, there is a csv with plans. this should be used to generate the two part product benefits slides. based on the csv, generate the two slides for each product:
{slides_text}

Return ONLY the markdown (content without ```), structured with appropriate headers, lists, and formatting. Do not include any JSON or explanatory text."""

        # Get the markdown content
        result = await get_completion(prompt)
        
        # Save the markdown content
        processed_path = deck_path / "ai" / "processed_content.md"
        with open(processed_path, 'w') as f:
            f.write(result)
                
        # Update state with the path to the processed content
        state["processed_content_path"] = str(processed_path)
            
    except Exception as e:
        state["error_context"] = {
            "step": "process_summaries",
            "error": str(e),
            "details": "Failed to process summaries"
        }
        
    return state 