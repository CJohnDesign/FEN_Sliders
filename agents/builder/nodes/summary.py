"""Summary generation node for the builder agent."""
import asyncio
import json
import base64
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..utils.logging_utils import setup_logger, log_async_step, log_step_result
from ..utils.retry_utils import retry_with_exponential_backoff
from ..config.models import get_model_config

# Set up logger
logger = setup_logger(__name__)

@retry_with_exponential_backoff(
    max_retries=3,
    min_seconds=4,
    max_seconds=10
)
def encode_image(image_path):
    """Convert an image file to base64 encoding with retry logic"""
    try:
        logger.info(f"Encoding image: {image_path}")
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            logger.info(f"Successfully encoded image: {image_path}")
            return encoded
    except Exception as e:
        logger.error(f"Error encoding image {image_path}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        raise

async def process_page(model, page_num, img_path, total_pages, title):
    """Process a single page with proper error handling and retries"""
    try:
        logger.info(f"Processing page {page_num} of {total_pages}")
        
        base64_image = encode_image(img_path)
        logger.info(f"Successfully encoded image for page {page_num}")
        
        messages = [
            SystemMessage(content=f"""You are an expert at analyzing presentation slides.
            You are analyzing a presentation titled: "{title}"
            
            Look at the slide and return a detailed summary of the content. Include a descriptive title and the summary should be a single paragraph that covers all details of the slide. In the summary, talk about which companies provide which benefits.
            * If there is a benefits table, return tableDetails.hasBenefitsTable as true
            ** Benefits tables can include, but not limited to, primary care visits, specialist visits, urgent care, and in-patient hospitalization benefits with specific co-pays and maximums. It can include Dental benefits plan, vision, etc. it will talk about the benefits you get with the plans.
            * If you identify a slide talks specifically about limitations, restrictions or exclusions about the insurance, return tableDetails.hasLimitations as true. This should never return true for a slide that has a benefits table.
            * if a slide has a benefits table, it will never have limitations.
            ** So both can be false but both can never be true.
            * Never use the word "comprehensive". These plans are never comprehensive so we should not say that.
            Provide your analysis in this EXACT JSON format:
            {{
                "title": "Clear descriptive title",
                "summary": "Detailed content summary",
                "tableDetails": {{
                    "hasBenefitsTable": true/false,
                    "hasLimitations": true/false
                }}
            }}"""),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"Analyze this slide from the '{title}' presentation systematically."
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
        
        logger.info(f"Sending request to model for page {page_num}")
        response = await model.ainvoke(messages)
        logger.info(f"Received response from model for page {page_num}")
        
        try:
            # Strip markdown code block formatting if present
            content_str = response.content
            if content_str.startswith("```json"):
                content_str = content_str.replace("```json", "", 1)
            if content_str.endswith("```"):
                content_str = content_str[:-3]
            content_str = content_str.strip()
            
            content = json.loads(content_str)
            logger.info(f"Successfully parsed response for page {page_num}")
            content["page"] = page_num
            return content
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response for page {page_num}: {str(e)}")
            logger.error(f"Raw response: {response.content}")
            raise
            
    except Exception as e:
        logger.error(f"Error processing page {page_num}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        return None

async def process_batch(model, batch_images, start_idx, total_pages, title):
    """Process a batch of pages concurrently"""
    tasks = []
    for idx, img_path in enumerate(batch_images, start=start_idx):
        tasks.append(process_page(model, idx, img_path, total_pages, title))
    return await asyncio.gather(*tasks)

async def process_raw_summaries(state: Dict, model: ChatOpenAI) -> str:
    """Process raw summaries into a structured format for slides and audio"""
    logger.info("Processing raw summaries into structured format")
    
    summaries = state.get("summaries", [])
    if not summaries:
        logger.error("No raw summaries found in state")
        return ""
        
    # Create messages for processing
    messages = [
        SystemMessage(content="""You are an expert at organizing presentation content.
        Take the raw summaries and organize them into a clear, structured format.
        Group related content together and create a logical flow.
        Identify key sections like:
        - Introduction/Overview
        - Benefits and Features
        - Plan Details
        - Costs and Coverage
        - Additional Services
        - Limitations and Exclusions
        
        Return the processed content in a clear markdown format that can be used
        for both slides and audio script generation."""),
        HumanMessage(content=f"""Process these raw summaries into a structured format:
        {json.dumps(summaries, indent=2)}
        
        Create a logical flow that groups related content and maintains all the important details.
        The output will be used to generate both slides and an audio script.""")
    ]
    
    # Get processed content
    logger.info("Sending request to model for summary processing")
    response = await model.ainvoke(messages)
    processed_content = response.content.strip()
    logger.info("Successfully processed summaries")
    
    return processed_content

async def process_summaries(state: Dict) -> Dict:
    """Process all pages to generate summaries"""
    logger.info("Starting summary processing")
    
    # Get the image directory path from deck_info
    deck_dir = Path(state["deck_info"]["path"])
    img_dir = deck_dir / "img" / "pages"
    logger.info(f"Processing images from: {img_dir}")
    
    # Initialize model with config
    model_config = get_model_config()
    model = ChatOpenAI(**model_config)
    title = state["metadata"]["title"]
    
    # Get list of PNG files
    png_files = sorted([f for f in os.listdir(img_dir) if f.endswith('.png')])
    total_pages = len(png_files)
    
    logger.info(f"Found {total_pages} pages to process")
    
    # Generate raw summaries
    summaries = []
    for i, png_file in enumerate(png_files):
        img_path = os.path.join(img_dir, png_file)
        summary = await process_page(model, i+1, img_path, total_pages, title)
        summaries.append(summary)
        
    state["summaries"] = summaries
    logger.info("Completed raw summary processing")
    
    # Process raw summaries into structured format
    processed_content = await process_raw_summaries(state, model)
    state["processed_summaries"] = processed_content
    logger.info("Completed summary processing and structuring")
    
    return state 