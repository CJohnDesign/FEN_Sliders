"""Summary generation node for the builder agent."""
import asyncio
import json
import base64
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from ...utils import llm_utils, deck_utils
from ..state import BuilderState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..utils.logging_utils import setup_logger, log_async_step, log_step_result
from ..utils.retry_utils import retry_with_exponential_backoff

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

async def process_page(model, page_num, img_path, total_pages):
    """Process a single page with proper error handling and retries"""
    try:
        logger.info(f"Processing page {page_num} of {total_pages}")
        
        base64_image = encode_image(img_path)
        logger.info(f"Successfully encoded image for page {page_num}")
        
        messages = [
            SystemMessage(content="""You are an expert presentation analyst.
            First work out the content structure before making conclusions.
            Analyze each element systematically:
            1. Text content and headings
            2. Table structures and data organization
            3. Visual elements and their purpose
            4. Key information hierarchy
            
            Then provide your analysis in this EXACT JSON format:
            {
                "title": "Clear descriptive title",
                "summary": "Detailed content summary",
                "tableDetails": {
                    "hasTable": true/false,
                    "type": "benefits/pricing/other"
                }
            }"""),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": "Analyze this presentation slide systematically."
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

async def process_batch(model, batch_images, start_idx, total_pages):
    """Process a batch of pages concurrently"""
    tasks = []
    for idx, img_path in enumerate(batch_images, start=start_idx):
        tasks.append(process_page(model, idx, img_path, total_pages))
    return await asyncio.gather(*tasks)

@log_async_step(logger)
async def generate_page_summaries(state: BuilderState) -> BuilderState:
    """Generate summaries for each page and save to JSON"""
    try:
        if state.get("error_context"):
            logger.warning("Error context found in state, skipping summary generation")
            return state
            
        if not state.get("pdf_info"):
            error_msg = "No PDF info available"
            logger.error(error_msg)
            state["error_context"] = {
                "error": error_msg,
                "stage": "summary_generation"
            }
            return state
            
        logger.info("Initializing LangChain chat model...")
        model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=4096,
            temperature=0.7,
            streaming=False
        )
        
        # Create ai directory if it doesn't exist
        ai_dir = Path(state["deck_info"]["path"]) / "ai"
        ai_dir.mkdir(exist_ok=True)
        logger.info(f"Created/verified AI directory at: {ai_dir}")
        
        # Get image paths from pdf_info
        image_paths = state["pdf_info"]["page_paths"]
        num_pages = state["pdf_info"]["num_pages"]
        logger.info(f"Found {len(image_paths)} image files to process")
        
        # Process pages in batches of 4 to balance concurrency and rate limits
        BATCH_SIZE = 4
        summaries = []
        checkpoint_file = ai_dir / "summaries_checkpoint.json"
        
        try:
            if checkpoint_file.exists():
                with open(checkpoint_file, "r") as f:
                    summaries = json.load(f)
                logger.info(f"Loaded {len(summaries)} summaries from checkpoint")
                
            # Calculate remaining pages
            processed_pages = {s["page"] for s in summaries}
            remaining_images = [(i+1, path) for i, path in enumerate(image_paths) 
                              if i+1 not in processed_pages]
            
            for batch_start in range(0, len(remaining_images), BATCH_SIZE):
                batch = remaining_images[batch_start:batch_start + BATCH_SIZE]
                batch_paths = [path for _, path in batch]
                start_idx = batch[0][0]
                
                logger.info(f"Processing batch starting at page {start_idx}")
                batch_results = await process_batch(model, batch_paths, start_idx, num_pages)
                
                # Filter out None results and add successful ones
                valid_results = [r for r in batch_results if r is not None]
                summaries.extend(valid_results)
                
                # Save checkpoint after each batch
                with open(checkpoint_file, "w") as f:
                    json.dump(summaries, f, indent=2)
                logger.info(f"Saved checkpoint with {len(summaries)} summaries")
                
                # Add small delay between batches
                await asyncio.sleep(2)
            
            # Sort summaries by page number
            summaries.sort(key=lambda x: x["page"])
            
            # Save final summaries
            summaries_file = ai_dir / "summaries.json"
            with open(summaries_file, "w") as f:
                json.dump(summaries, f, indent=2)
            logger.info(f"Saved {len(summaries)} summaries to {summaries_file}")
            
            # Clean up checkpoint file
            if checkpoint_file.exists():
                checkpoint_file.unlink()
            
            # Update state
            state["page_summaries"] = summaries
            
            log_step_result(
                logger,
                "summary_generation",
                True,
                f"Generated {len(summaries)} page summaries"
            )
            return state
            
        except Exception as e:
            logger.error("Error during batch processing")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("Full error context:", exc_info=True)
            
            # Save progress to checkpoint if we have any summaries
            if summaries:
                with open(checkpoint_file, "w") as f:
                    json.dump(summaries, f, indent=2)
                logger.info(f"Saved progress to checkpoint with {len(summaries)} summaries")
            
            state["error_context"] = {
                "error": str(e),
                "stage": "summary_generation",
                "progress": len(summaries)
            }
            return state
            
    except Exception as e:
        log_step_result(
            logger,
            "summary_generation",
            False,
            f"Failed to generate summaries: {str(e)}"
        )
        state["error_context"] = {
            "error": str(e),
            "stage": "summary_generation"
        }
        return state

async def process_plan_tiers(state: BuilderState) -> BuilderState:
    """Process benefit tables into detailed plan tier summaries"""
    try:
        deck_dir = Path(state["deck_info"]["path"])
        tables_data = deck_utils.load_tables_data(deck_dir)
        
        if not tables_data["tables"]:
            logger.warning("No tables found for plan tier processing")
            state["plan_tier_summaries"] = "No plan tiers found in document"
            return state
            
        # Initialize chat model
        model = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            streaming=False,
            max_tokens=4096
        )
        
        # Create system prompt
        system_content = """You are an expert at analyzing insurance benefit tables and creating clear plan tier summaries.
        
        Analyze the provided tables and create a detailed markdown summary that:
        1. Clearly identifies each plan tier
        2. Lists all benefits and coverage details
        3. Maintains exact dollar amounts and percentages
        4. Highlights key differences between tiers
        5. Uses clear formatting and structure
        
        Format the output as a clean markdown section that can be inserted directly into a presentation outline."""
        
        # Convert tables to text format
        tables_text = json.dumps(tables_data, indent=2)
        
        # Create messages
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=f"""Analyze these benefit tables and create a detailed plan tier summary:

{tables_text}

Focus on:
1. Exact benefit amounts
2. Coverage percentages
3. Key limitations
4. Tier differences""")
        ]
        
        # Generate summary
        response = await model.ainvoke(messages)
        
        # Save to state
        state["plan_tier_summaries"] = response.content
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "step": "plan_tier_processing",
            "error": str(e)
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
            
        # First process plan tiers
        state = await process_plan_tiers(state)
        if state.get("error_context"):
            return state
            
        if not state.get("plan_tier_summaries"):
            state["error_context"] = {
                "step": "process_summaries",
                "error": "Plan tier processing failed"
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
        
        # Create system prompt using plan tier summaries
        system_content = """You are an expert at organizing and structuring content for presentations. Your task is to generate a comprehensive markdown outline that organizes all insurance benefit information in an educational format.

IMPORTANT: The outline MUST maintain the exact plan tier information provided, including all benefit amounts and structure.

The outline must follow this EXACT structure:

## Cover
- Plan name
- Subtitle

## Core Plan Elements
- **Introduction & Overview**
  - Plan purpose and scope
  - Association membership (BWA, NCE, etc.)
  - Basic coverage framework
  - Key insurance concepts and terms

## Common Service Features
- **Telehealth Services**
  - Availability and access
  - Covered services
- **Preventive Care & Wellness**
  - Available programs
  - Coverage details
- **Advocacy & Support**
  - Member services
  - Support resources
- **Medical Bill Management**
  - Billing assistance
  - Payment processing
  
## Plan Tiers and Benefits
- Here, analyze the benefit tables and create a detailed plan tier summary.
  - atleast one slide per tier
  - If a slide gets too long, split it into two sections.
    - label these section with a (1/2) or (2/2)
  - its likely that the later tiers will be more detailed and require a 2nd slide

## Limitations & Definitions
- **Required Disclosures**
  - Coverage limitations
  - State-specific information
  - Important definitions
  - Policy terms

## Key Takeaways
- Plan comparison highlights
- Value propositions
- Important reminders
- Next steps

CRITICAL REQUIREMENTS:
1. The Plan Tiers section MUST come first
2. Use the EXACT plan tier content provided
3. Do not modify or summarize the plan tier information
4. Maintain all specific benefit amounts and details
5. Keep the two-part structure for each plan"""

        # Get tables data from state
        deck_dir = Path(state["deck_info"]["path"])
        tables_data = deck_utils.load_tables_data(deck_dir)
        tables_text = json.dumps(tables_data, indent=2)

        # Insert the plan tier summaries and tables data
        system_content = system_content.format(
            tables_data=tables_text,
            plan_tier_summaries=state["plan_tier_summaries"]
        )

        # Get plan tier summaries from state
        plan_tier_summaries = state.get("plan_tier_summaries", "No plan tier analysis available")

        # Create messages array
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=f"""Create a comprehensive benefit overview that:
1. Keeps the Plan Tiers section EXACTLY as provided
2. Uses the general summaries to enhance other sections
3. Maintains all specific benefit amounts
4. Creates clear explanations of insurance concepts
5. Includes relevant policy details

The Plan Tiers section has already been processed and must be kept intact.
Focus on enhancing the other sections while preserving the plan tier information.

Here are the general summaries to incorporate:

{summaries_text}

  ## Plan Tiers and Benefits
### Raw Benefit Tables
{tables_data}

### Plan Tier Analysis
{plan_tier_summaries}

""")
        ]
        
        # Generate content
        response = await model.ainvoke(messages)
        content = response.content
        
        # Verify plan tiers section is present and in the correct position
        if "## 1. Plan Tiers" not in content or content.find("## 1. Plan Tiers") > content.find("## 2."):
            # Force correct structure if needed
            sections = content.split("##")
            reordered_content = "##" + sections[0]  # Keep any initial content
            reordered_content += "\n## 1. Plan Tiers\n" + state["plan_tier_summaries"] + "\n"
            for section in sections[1:]:
                if not section.strip().startswith("1. Plan Tiers"):
                    reordered_content += "##" + section
            content = reordered_content
        
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