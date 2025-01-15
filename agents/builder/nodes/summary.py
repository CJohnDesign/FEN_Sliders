import asyncio
import json
import base64
import logging
from pathlib import Path
from ...utils import llm_utils
from ..state import BuilderState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logging.basicConfig(
    filename='builder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def encode_image(image_path):
    """Convert an image file to base64 encoding"""
    try:
        with open(image_path, "rb") as image_file:
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
            
        # Initialize LangChain chat model for proper tracing
        model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=1024,
            temperature=0.7,
            streaming=False,
            tags=["image_analysis", "summary_generation"],
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        
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
                    
                    try:
                        base64_image = encode_image(img_path)
                    except Exception as e:
                        logging.error(f"Failed to encode image for page {page_num}: {str(e)}")
                        continue
                        
                    for retry in range(max_retries):
                        try:
                            messages = [
                                SystemMessage(content="""You are an expert presentation analyst.
                                Your task is to analyze presentation content and provide:
                                1. A clear, descriptive title for the content
                                2. A detailed summary of the content
                                3. Whether the content contains any tables or tabular data
                                
                                Return as a JSON object with `title`, `summary`, and `hasTable` fields.
                                The `hasTable` field should be a boolean indicating if the content contains any tables."""),
                                HumanMessage(content=[
                                    {
                                        "type": "text",
                                        "text": f"This is page {page_num} of {state['pdf_info']['page_count']}. Please analyze it and provide a title, summary, and whether it contains tables in JSON format."
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}",
                                            "detail": "high"
                                        }
                                    }
                                ])
                            ]
                            
                            response = await model.ainvoke(messages)
                            
                            try:
                                content = json.loads(response.content)
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
                            except json.JSONDecodeError as e:
                                if retry == max_retries - 1:
                                    logging.error(f"Failed to parse JSON for page {page_num}: {str(e)}")
                                    summaries.append({
                                        "page": page_num,
                                        "title": "Error: Could not parse response",
                                        "summary": "Error processing page",
                                        "hasTable": False
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
                                    "summary": f"Failed to generate summary: {error_msg}",
                                    "hasTable": False
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

async def process_summaries(state: BuilderState) -> BuilderState:
    """Processes summaries to generate markdown content"""
    try:
        if state.get("error_context"):
            return state
            
        if not state.get("page_summaries"):
            state["error_context"] = {
                "step": "process_summaries",
                "error": "No page summaries available"
            }
            return state
            
        # Convert summaries to text
        summaries_text = json.dumps(state["page_summaries"], indent=2)
        
        # Initialize LangChain chat model for proper tracing
        model = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            streaming=False,
            tags=["summary_processing", "markdown_generation"]
        )
        
        # Extract CSV data from summaries
        csv_data = None
        for summary in state["page_summaries"]:
            if summary.get("hasTable") and summary.get("csv"):
                # CSV is already clean, use it directly
                csv_data = summary["csv"]
                break
        
        # Create system prompt with CSV data if available
        system_content = """You are an expert at organizing and structuring content for presentations. Your task is to generate a markdown outline that organizes content in an educational format.

The outline should:
## 1. Core Plan Elements
- **Introduction & Overview**
  - Plan purpose and scope
  - Association membership (BWA, NCE, etc.)
  - Basic coverage framework

## 2. Common Service Features
- **Telehealth Services**
- **Preventive Care & Wellness**
- **Advocacy & Support**
- **Medical Bill Management**

## 3. Plan Tiers (each plan has 2 tiers)

<!-- Return sets of two for each plan -->

### Plans 1 (1/2)
- Benefits details list

### Plans 1 (2/2)
- Benefits details list"""

        # Add CSV data if available
        if csv_data:
            system_content += f"\n\nHere is the CSV data of benefits:\n{csv_data}\n\n"

        system_content += """
## 4. Limitations & Definitions
- **Required Disclosures**

## 5. Key Takeaways
- Plan comparison highlights
- Important reminders"""
        
        # Create messages array
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=f"Please organize the following summaries into a structured markdown outline:\n\n{summaries_text}")
        ]
        
        # Generate content
        response = await model.ainvoke(messages)
        content = response.content
        
        # Save content
        script_path = Path(state["deck_info"]["path"]) / "ai" / "processed_summaries.md"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(script_path, "w") as f:
            f.write(content)
            
        # Set processed summaries in state
        state["processed_summaries"] = content
            
        return state
        
    except Exception as e:
        state["error_context"] = {
            "step": "process_summaries",
            "error": str(e)
        }
        return state 