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
            SystemMessage(content="""You are an expert at analyzing presentation slides.
            Look at the slide and return a detailed summary of the content. it should be a single paragraph that covers all details of the slide.
            If there is a table, identify if it is a benefits table showing insurance coverage details and return tableDetails.hasTable as true.
            If you identify a slide has limitations, restrictions or declarions about the insurance limitations and return tableDetails.hasLimitations as true.
            
            Provide your analysis in this EXACT JSON format:
            {
                "title": "Clear descriptive title",
                "summary": "Detailed content summary",
                "tableDetails": {
                    "hasTable": true/false,
                    "hasLimitations": true/false,
                    "mentionedCompanies": ["Company Name 1", "Company Name 2", "Company Name 3"]
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
            max_tokens=8000,
            temperature=0.2,
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
        
        # Save to file
        summaries_path = deck_dir / "ai" / "plan_tier_summaries.md"
        with open(summaries_path, "w") as f:
            f.write(response.content)
        logger.info(f"Saved plan tier summaries to {summaries_path}")
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "step": "plan_tier_processing",
            "error": str(e)
        }
        return state

async def process_summaries(state: Dict) -> Dict:
    """Process summaries to generate markdown content"""
    try:
        if state.get("error_context"):
            return state
            
        if not state.get("page_summaries"):
            state["error_context"] = {
                "step": "process_summaries",
                "error": "Processed summaries not found"
            }
            return state
            
        # Try to get plan tier summaries from state or file
        deck_dir = Path(state["deck_info"]["path"])
        if not state.get("plan_tier_summaries"):
            plan_tier_path = deck_dir / "ai" / "plan_tier_summaries.md"
            if plan_tier_path.exists():
                with open(plan_tier_path, "r") as f:
                    state["plan_tier_summaries"] = f.read()
                logger.info("Loaded plan tier summaries from file")
            else:
                state["error_context"] = {
                    "step": "process_summaries",
                    "error": "Plan tier summaries not found in state or file"
                }
                return state

        # Get tables data from state
        tables_data = deck_utils.load_tables_data(deck_dir)
        tables_text = json.dumps(tables_data, indent=2)

        # Convert summaries to text
        summaries_text = json.dumps(state["page_summaries"], indent=2)
        
        # Initialize chat model
        model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=4096,
            temperature=0.7
        )
        
        # Create system prompt
        system_content = """Create a comprehensive benefit overview that follows this structure:

## Plan Overview

## Core Plan Elements

## Common Service Features

## Plan Tiers and Benefits 
**There will be many sections here, return all plans with their benefits.**

## Comparison of the Plans

## Limitations and Definitions

## Key Takeaways

CRITICAL REQUIREMENTS:
1. Use the EXACT content provided for both tables and analysis - do not modify this information
2. Maintain all specific benefit amounts and details
3. Enhance other sections while preserving the exact plan tier information"""

        # Get plan tier summaries from state or set default
        plan_tier_summaries = state.get("plan_tier_summaries", "No plan tier analysis available")

        # Insert the plan tier summaries and tables data
        system_content = system_content.format(
            tables_data=tables_text,
            plan_tier_summaries=plan_tier_summaries
        )

        # Create messages array
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=f"""Create a comprehensive benefit overview.
                         
Here are the general summaries to use:
{summaries_text}
                   
---

Here is the plan overview below. I'm insertings the plan tier summaries and tables data into the appropriate sections:                   
                         
## Plan Overview
- Subheading

## Core Plan Elements
- Key features and benefits
- Coverage details
- Eligibility requirements

## Common Service Features
- Network access
- Claims process
- Support services

## Plan Tiers and Benefits

* Based on the below, create one page for each plan tier with benefits for each tier.
* If a slide is too long, break it into multiple slides, ie (1/2) and (2/2)
** It is likely that the higher plans will have more benefits and require this.

- Plan Tier Analysis
{plan_tier_summaries}

- Raw Benefit Tables
{tables_data}

Below is the format of a single plan tier, broken into 2 parts. Create a new section for each plan tier. This is not a strict template, but a general format to follow. Create a new section for each plan tier. if a section is short, it will not require a second part. Higher plans will have more benefits and will require a second section.

## Plan 4 Name (1/2)

**Benefit Category 1**
- Detail 1: Value 1
- Detail 2: Value 2
- Detail 3: Value 3
- Detail 4: Value 4

**Benefit Category 2**
- Detail 1: Value 1
- Detail 2: Value 2

**Benefit Category 3**
- Detail 1: Value 1
- Detail 2: Value 2
- Detail 3: Value 3


## Plan 4 Name (2/2)

**Benefit Category 4**
- Detail 1: Value 1
- Detail 2: Value 2

**Benefit Category 5**
- Detail 1: Value 1
- Detail 2: Value 2


## Comparing the Plans

| **Feature** | **Plan 1** | **Plan 2** | **Plan 3** |
|---------|----------|----------|-----------|
| Feature 1 | Value 1.1 | Value 1.2 | Value 1.3 |
| Feature 2 | Value 2.1 | Value 2.2 | Value 2.3 |
| Feature 3 | Value 3.1 | Value 3.2 | Value 3.3 |
| Feature 4 | Value 4.1 | Value 4.2 | Value 4.3 |
| Feature 5 | Value 5.1 | Value 5.2 | Value 5.3 |

* If the content is too long, break the comparing plans section into multiple slides. ie (1/2) and (2/2)

## Limitations and Definitions
- Important exclusions
- Key terms defined

## Key Takeaways
- Plan highlights
- Value propositions
- Next steps

The Plan Tiers and Benefits section has already been processed and must be kept intact.
Focus on enhancing the other sections while preserving both the tables and plan tier information.
""")
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
        logger.error(f"Error in process_summaries: {str(e)}")
        state["error_context"] = {
            "step": "process_summaries",
            "error": str(e)
        }
        return state 