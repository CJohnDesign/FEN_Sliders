"""Summary generation node for the builder agent."""
import asyncio
import json
import base64
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from ..state import BuilderState
from ...utils.content import save_content
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

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

def sanitize_filename(title: str) -> str:
    """Convert title to a valid filename."""
    # Replace spaces and special characters
    sanitized = title.lower().replace(' ', '_')
    # Remove any non-alphanumeric characters except underscores and hyphens
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c in '_-')
    return sanitized

async def process_page(model, page_num, img_path, total_pages, title):
    """Process a single page with proper error handling and retries"""
    try:
        logger.info(f"Processing page {page_num} of {total_pages}")
        
        base64_image = encode_image(img_path)
        logger.info(f"Successfully encoded image for page {page_num}")
        
        messages = [
            {
                "role": "system",
                "content": f"""You are an expert at analyzing presentation slides.
                You are analyzing a presentation titled: "{title}"
                
                Look at the slide and return:
                1. A clear, descriptive title for the slide (3-7 words)
                2. A detailed summary of the content in a single paragraph
                3. Information about tables and limitations
                
                The title should be descriptive and specific, not generic. For example:
                - Good: "Primary Care and Specialist Copays"
                - Bad: "Benefits Overview"
                
                * If there is a benefits table, return tableDetails.hasBenefitsTable as true
                ** Benefits tables can include, but not limited to, primary care visits, specialist visits, urgent care, and in-patient hospitalization benefits with specific co-pays and maximums. It can include Dental benefits plan, vision, etc. it will talk about the benefits you get with the plans.
                * If you identify a slide talks specifically about limitations, restrictions or exclusions about the insurance, return tableDetails.hasLimitations as true. This should never return true for a slide that has a benefits table.
                * if a slide has a benefits table, it will never have limitations.
                ** So both can be false but both can never be true.
                * Never use the word "comprehensive". These plans are never comprehensive so we should not say that.
                
                Provide your analysis in this EXACT JSON format:
                {{
                    "page_title": "Clear descriptive title",
                    "title": "Same as page_title",
                    "summary": "Detailed content summary",
                    "tableDetails": {{
                        "hasBenefitsTable": true/false,
                        "hasLimitations": true/false
                    }}
                }}"""
            },
            {
                "role": "user",
                "content": [
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
                ]
            }
        ]
        
        logger.info(f"Sending request to model for page {page_num}")
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        logger.info(f"Received response from model for page {page_num}")
        
        try:
            # Strip markdown code block formatting if present
            content_str = response.choices[0].message.content
            if content_str.startswith("```json"):
                content_str = content_str.replace("```json", "", 1)
            if content_str.endswith("```"):
                content_str = content_str[:-3]
            content_str = content_str.strip()
            
            content = json.loads(content_str)
            logger.info(f"Successfully parsed response for page {page_num}")
            
            # Add page number to content
            content["page"] = page_num
            
            # Rename the image file with the page title
            img_dir = Path(img_path).parent
            old_path = Path(img_path)
            sanitized_title = sanitize_filename(content["page_title"])
            new_filename = f"{page_num:02d}_{sanitized_title}.png"
            new_path = img_dir / new_filename
            
            # Rename the file
            old_path.rename(new_path)
            logger.info(f"Renamed image from {old_path.name} to {new_filename}")
            
            return content
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response for page {page_num}: {str(e)}")
            logger.error(f"Raw response: {content_str}")
            raise
            
    except Exception as e:
        logger.error(f"Error processing page {page_num}: {str(e)}")
        logger.error("Full error context:", exc_info=True)
        raise

async def process_raw_summaries(state: Dict) -> str:
    """Process raw summaries into a structured format for slides and audio"""
    logger.info("Processing raw summaries into structured format")
    
    summaries = state.get("summaries", [])
    if not summaries:
        logger.error("No raw summaries found in state")
        return ""
        
    # Create messages for processing
    messages = [
        {
            "role": "system",
            "content": """You are an expert at organizing presentation content.
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
            for both slides and audio script generation."""
        },
        {
            "role": "user",
            "content": f"""Process these raw summaries into a structured format:
            {json.dumps(summaries, indent=2)}
            
            Create a logical flow that groups related content and maintains all the important details.
            The output will be used to generate both slides and an audio script."""
        }
    ]
    
    # Get processed content
    logger.info("Sending request to model for summary processing")
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=4000
    )
    processed_content = response.choices[0].message.content.strip()
    logger.info("Successfully processed summaries")
    
    return processed_content

@traceable(name="process_summaries")
async def process_summaries(state: Dict) -> Dict:
    """Process all pages to generate summaries"""
    logger.info("Starting summary processing")
    
    # Get the image directory path from deck_info
    deck_dir = Path(state["deck_info"]["path"])
    img_dir = deck_dir / "img" / "pages"
    logger.info(f"Processing images from: {img_dir}")
    
    # Initialize model
    title = state["metadata"]["title"]
    
    # Get list of PNG files
    png_files = sorted([f for f in os.listdir(img_dir) if f.endswith('.png')])
    total_pages = len(png_files)
    
    logger.info(f"Found {total_pages} pages to process")
    
    # Generate raw summaries
    summaries = []
    for i, png_file in enumerate(png_files):
        img_path = os.path.join(img_dir, png_file)
        summary = await process_page(client, i+1, img_path, total_pages, title)
        summaries.append(summary)
        
    state["summaries"] = summaries
    logger.info("Completed raw summary processing")
    
    # Process raw summaries into structured format
    processed_content = await process_raw_summaries(state)
    state["processed_summaries"] = processed_content
    logger.info("Completed summary processing and structuring")
    
    return state 