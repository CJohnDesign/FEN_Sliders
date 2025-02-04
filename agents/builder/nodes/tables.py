"""Table extraction node for processing tables in slides."""
import logging
import os
import base64
import json
import asyncio
import traceback
from pathlib import Path
from typing import List, Dict, Any, Tuple
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from ..state import BuilderState, TableData, PageMetadata, PageSummary, WorkflowStage
from ...utils.llm_utils import get_llm
from ..utils.logging_utils import log_state_change, log_error
from ..utils.state_utils import save_state
from ..prompts.summary_prompts import TABLE_EXTRACTION_PROMPT

# Set up logging
logger = logging.getLogger(__name__)

BATCH_SIZE = 5

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64.
    WARNING: The returned base64 string should never be logged or stored in state.
    It should only be used for immediate processing and then discarded.
    """
    with open(image_path, "rb") as image_file:
        # Get file extension to determine mime type
        ext = Path(image_path).suffix.lower()
        mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
        # Create proper data URL format
        return f"data:{mime_type};base64,{base64.b64encode(image_file.read()).decode('utf-8')}"

async def create_table_chain():
    """Create the chain for extracting table data."""
    # Use centralized LLM configuration
    llm = await get_llm(
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    # Create prompt template using imported prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", TABLE_EXTRACTION_PROMPT),
        ("human", [
            {"type": "text", "text": "Please extract any tables from this slide."},
            {"type": "image_url", "image_url": "{image_data}"}
        ])
    ])
    
    return prompt | llm

async def process_page_batch(
    batch: List[Tuple[PageSummary, str]], 
    chain
) -> Dict[int, TableData]:
    """Process a batch of pages concurrently."""
    async def process_single_page(summary: PageSummary) -> Tuple[int, TableData]:
        try:
            if not os.path.exists(summary.file_path):
                logger.error(f"Image not found: {summary.file_path}")
                logger.error(f"Current directory: {os.getcwd()}")
                return summary.page_number, None
                
            # Encode image - base64 data should not be logged
            image_data = encode_image_to_base64(summary.file_path)
                
            # Extract table data
            response = await chain.ainvoke({"image_data": image_data})
            
            # Clear the image data from memory explicitly
            del image_data
            
            # Parse JSON response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError as json_error:
                logger.error(f"Failed to parse JSON for page {summary.page_number}: {str(json_error)}")
                logger.error(f"Response content: {response.content[:100]}...")  # Log first 100 chars
                return summary.page_number, None
            
            # Validate response structure
            required_fields = ["headers", "rows", "table_type", "metadata"]
            if not all(field in result for field in required_fields):
                logger.error(f"Missing required fields in response for page {summary.page_number}")
                logger.error(f"Got fields: {list(result.keys())}")
                return summary.page_number, None
            
            # Convert to TableData
            table_data = TableData(
                headers=result["headers"],
                rows=result["rows"],
                table_type=result["table_type"],
                metadata=result["metadata"]
            )
            
            logger.info(f"Extracted table from page {summary.page_number} ({len(table_data.rows)} rows)")
            
            return summary.page_number, table_data
            
        except Exception as e:
            logger.error(f"Failed to process page {summary.page_number}: {str(e)}")
            logger.error(traceback.format_exc())
            return summary.page_number, None

    # Process batch concurrently
    tasks = [process_single_page(summary) for summary, _ in batch]
    results = await asyncio.gather(*tasks)
    
    # Filter out failed results and convert to dict
    return {page_num: data for page_num, data in results if data is not None}

async def extract_tables(state: BuilderState) -> BuilderState:
    """Extract and process tables from slides."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.EXTRACT_TABLES:
            logger.warning(f"Expected stage {WorkflowStage.EXTRACT_TABLES}, but got {state.current_stage}")
            
        # Validate input state
        if not state.page_summaries:
            logger.error("No page summaries found in state")
            return state
            
        logger.info(f"Starting table extraction with {len(state.page_summaries)} summaries")
        logger.info(f"Summary page numbers: {[s.page_number for s in state.page_summaries]}")
            
        # Get pages with tables directly from summaries
        pages_with_tables = [
            (summary, summary.file_path) 
            for summary in state.page_summaries 
            if summary.has_tables
        ]
        
        if not pages_with_tables:
            logger.info("No tables to process")
            return state
            
        logger.info(f"Found {len(pages_with_tables)} pages with tables:")
        for summary, path in pages_with_tables:
            logger.info(f"  - Page {summary.page_number}: {summary.page_name}")
            if not os.path.exists(path):
                logger.error(f"    Warning: File not found at {path}")
                logger.error(f"    Current directory: {os.getcwd()}")
                logger.error(f"    Is absolute path: {os.path.isabs(path)}")
        
        # Create table chain
        chain = await create_table_chain()
        
        # Process pages in batches
        tables_data = {}
        total_batches = (len(pages_with_tables) + BATCH_SIZE - 1) // BATCH_SIZE
        
        try:
            for i in range(0, len(pages_with_tables), BATCH_SIZE):
                batch = pages_with_tables[i:i + BATCH_SIZE]
                current_batch = i // BATCH_SIZE + 1
                logger.info(f"Processing batch {current_batch}/{total_batches}")
                logger.info(f"Batch pages: {[s.page_number for s, _ in batch]}")
                
                try:
                    batch_results = await process_page_batch(batch, chain)
                    if batch_results:
                        tables_data.update(batch_results)
                        logger.info(f"Batch {current_batch} complete - extracted {len(batch_results)} tables")
                        for page_num, table in batch_results.items():
                            logger.info(f"  - Page {page_num}: {len(table.rows)} rows, {len(table.headers)} columns")
                            logger.info(f"    Headers: {table.headers}")
                    else:
                        logger.error(f"Batch {current_batch} failed to process")
                except Exception as batch_error:
                    logger.error(f"Error in batch {current_batch}: {str(batch_error)}")
                    logger.error(traceback.format_exc())
                    continue
        except Exception as batch_loop_error:
            logger.error(f"Error in batch processing loop: {str(batch_loop_error)}")
            logger.error(traceback.format_exc())
            
        if not tables_data:
            logger.error("No tables were extracted")
            return state
            
        # Update state with structured table data
        state.tables_data = tables_data
        
        logger.info(f"Table extraction completed. Processed {len(tables_data)} tables")
        logger.info(f"Pages with extracted tables: {sorted(tables_data.keys())}")
        
        # Validate final state
        if not state.tables_data:
            logger.error("Final state validation failed - no tables data")
            return state
            
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="extract_tables",
            change_type="complete",
            details={
                "tables_count": len(state.tables_data or {}),
                "pages_with_tables": sorted(list(state.tables_data.keys())) if state.tables_data else []
            }
        )
        
        # Update workflow stage
        state.update_stage(WorkflowStage.EXTRACT_TABLES)
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "extract_tables", e)
        state.error_context = {
            "error": str(e),
            "stage": "table_extraction",
            "traceback": traceback.format_exc()
        }
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 