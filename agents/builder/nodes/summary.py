"""Summary processing node for extracting and processing page summaries."""
import logging
from typing import List, Dict, Any
from pathlib import Path
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema.messages import HumanMessage, SystemMessage
from ..state import BuilderState, PageMetadata, PageSummary
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
import base64
import os
import json

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Reduce verbosity

def get_page_metadata(state: BuilderState) -> List[PageMetadata]:
    """Get metadata for each page from state."""
    try:
        if not state.page_metadata:
            logger.warning("No page metadata found in state")
            return []
            
        return state.page_metadata
        
    except Exception as e:
        logger.error(f"Error getting page metadata: {str(e)}")
        return []

async def create_summary_chain():
    """Create the chain for generating page summaries."""
    # Use centralized LLM configuration with JSON response format
    llm = await get_llm(
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    # Create prompt template with proper message structure
    system_prompt = """You are an expert at analyzing presentation slides. You must output a JSON object that matches this exact structure:

{{
    "page_title": "long_and_descriptive_title_that_summarizes_the_content_of_the_slide",
    "summary": "Detailed content summary with multiple paragraphs",
    "tableDetails": {{
        "hasBenefitsTable": true,
        "hasLimitations": false
    }},
    "page": 1
}}

Analyze the slide and provide:
1. A clear descriptive title that captures the main topic. this will be later saved as the filename
2. A detailed multi-paragraph summary of the content
3. Indicate if the slide contains benefit tables or limitations

YOUR RESPONSE MUST BE A VALID JSON OBJECT."""

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", [
            {"type": "text", "text": "Please analyze this slide."},
            {"type": "image_url", "image_url": "{image_url}"}
        ])
    ])
    
    # Create chain that runs synchronously
    chain = prompt | llm
    
    return chain

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64."""
    with open(image_path, "rb") as image_file:
        return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"

async def process_page_content(
    state: BuilderState,
    page_metadata: PageMetadata
) -> PageSummary:
    """Process content for a single page."""
    try:
        # Create summary chain
        chain = await create_summary_chain()
        
        # Get full path to image file
        image_path = os.path.join(state.deck_info.path, page_metadata.file_path)
        
        # Encode image to base64
        image_url = encode_image_to_base64(image_path)
            
        # Generate summary using proper message structure
        response = await chain.ainvoke({
            "image_url": image_url
        })
        
        # Parse the JSON content from the response
        result = json.loads(response.content)
        
        # Create PageSummary from result
        return PageSummary(
            page_number=page_metadata.page_number,
            page_name=result["title"],
            summary=result["summary"],
            key_points=[],  # We'll get these from processed_summaries later
            action_items=[],  # We'll get these from processed_summaries later
            has_tables=result["tableDetails"]["hasBenefitsTable"],
            has_limitations=result["tableDetails"]["hasLimitations"]
        )
        
    except Exception as e:
        logger.error(f"Error processing page {page_metadata.page_number}: {str(e)}")
        return PageSummary(
            page_number=page_metadata.page_number,
            page_name=page_metadata.page_name,
            summary="Error processing page",
            key_points=[],
            action_items=[],
            has_tables=False,
            has_limitations=False
        )

async def process_summaries(state: BuilderState) -> BuilderState:
    """Process summaries for all pages."""
    try:
        # Get image directory
        pages_dir = Path(state.deck_info.path) / "img" / "pages"
        if not pages_dir.exists():
            logger.error("Pages directory not found")
            return state
            
        # Get all images
        image_files = sorted(pages_dir.glob("*.jpg"))
        if not image_files:
            image_files = sorted(pages_dir.glob("*.png"))
        
        if not image_files:
            logger.error("No image files found")
            return state
            
        # Create summary chain
        chain = await create_summary_chain()
        
        # Process each image
        summaries = []
        raw_summaries = []  # Store raw summaries for downstream processing
        
        for i, image_path in enumerate(image_files, 1):
            try:
                # Encode image
                image_url = encode_image_to_base64(str(image_path))
                
                # Generate summary using proper message structure
                response = await chain.ainvoke({
                    "image_url": image_url
                })
                
                # Parse the JSON content from the response
                result = json.loads(response.content)
                
                # Store raw summary for downstream processing
                raw_summary = {
                    "title": result["title"],
                    "summary": result["summary"],
                    "tableDetails": result["tableDetails"],
                    "page": i
                }
                raw_summaries.append(raw_summary)
                
                # Create summary for state
                summary = PageSummary(
                    page_number=i,
                    page_name=result["title"],
                    summary=result["summary"],
                    key_points=[],  # We'll get these from processed_summaries later
                    action_items=[],  # We'll get these from processed_summaries later
                    has_tables=result["tableDetails"]["hasBenefitsTable"],
                    has_limitations=result["tableDetails"]["hasLimitations"]
                )
                summaries.append(summary)
                
                # Only log important progress
                if i % 5 == 0:  # Log every 5th page
                    logger.info(f"Processed {i}/{len(image_files)} pages")
                
            except Exception as e:
                logger.error(f"Error processing image {image_path.name}: {str(e)}")
                continue
            
        # Update state with summaries
        state.page_summaries = summaries
        
        # Save raw summaries for downstream processing
        summaries_dir = Path(state.deck_info.path) / "ai"
        summaries_dir.mkdir(parents=True, exist_ok=True)
        with open(summaries_dir / "summaries.json", "w") as f:
            json.dump(raw_summaries, f, indent=2)
        
        # Log final completion
        logger.info(f"Completed processing {len(summaries)} pages")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in process_summaries: {str(e)}")
        return state 