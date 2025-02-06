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
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

BATCH_SIZE = 5

@traceable(name="encode_image")
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

@traceable(name="create_table_chain")
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

@traceable(name="process_page_batch")
async def process_page_batch(
    batch: List[Tuple[PageSummary, str]], 
    chain,
    state: BuilderState,
    batch_number: int,
    total_batches: int
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
    
    # Update progress
    state.set_stage_progress(
        total=4,  # setup, chain creation, batch processing, finalization
        completed=2,
        current=f"Processing batch {batch_number}/{total_batches}"
    )
    
    # Filter out failed results and convert to dict
    return {page_num: data for page_num, data in results if data is not None}

@traceable(name="extract_tables")
async def extract_tables(state: BuilderState) -> BuilderState:
    """Extract and process tables from slides."""
    try:
        logger.info("Starting table extraction")
        
        # Verify we're in the correct stage
        if state.workflow_progress.current_stage != WorkflowStage.PROCESS:
            logger.warning(f"Expected stage {WorkflowStage.PROCESS}, got {state.workflow_progress.current_stage}")
            state.update_stage(WorkflowStage.PROCESS)
            
        # Initialize stage progress
        state.set_stage_progress(
            total=4,  # setup, chain creation, batch processing, finalization
            completed=0,
            current="Initializing table extraction"
        )
            
        # Validate input state
        if not state.page_summaries:
            error_msg = "No page summaries found in state"
            logger.error(error_msg)
            state.set_error(error_msg, "extract_tables")
            return state
            
        logger.info(f"Starting table extraction with {len(state.page_summaries)} summaries")
        logger.info(f"Summary page numbers: {[s.page_number for s in state.page_summaries]}")
            
        # Get pages with tables directly from summaries
        pages_with_tables = [
            (summary, summary.file_path) 
            for summary in state.page_summaries 
            if summary.tableDetails.hasBenefitsTable  # Only process pages with benefits tables
        ]
        
        if not pages_with_tables:
            logger.info("No benefits tables to process")
            state.set_stage_progress(
                total=4,
                completed=4,
                current="No benefits tables found to process"
            )
            return state
            
        logger.info(f"Found {len(pages_with_tables)} pages with tables:")
        for summary, path in pages_with_tables:
            logger.info(f"  - Page {summary.page_number}: {summary.page_name}")
            
        # Update progress after setup
        state.set_stage_progress(
            total=4,
            completed=1,
            current="Setup complete, creating extraction chain"
        )
            
        # Create table chain
        chain = await create_table_chain()
        
        # Process pages in batches
        tables_data = []
        total_batches = (len(pages_with_tables) + BATCH_SIZE - 1) // BATCH_SIZE
        
        try:
            for i in range(0, len(pages_with_tables), BATCH_SIZE):
                batch = pages_with_tables[i:i + BATCH_SIZE]
                current_batch = i // BATCH_SIZE + 1
                logger.info(f"Processing batch {current_batch}/{total_batches}")
                logger.info(f"Batch pages: {[s.page_number for s, _ in batch]}")
                
                try:
                    batch_results = await process_page_batch(
                        batch, 
                        chain, 
                        state,
                        current_batch,
                        total_batches
                    )
                    if batch_results:
                        for page_num, table in batch_results.items():
                            if table:
                                tables_data.append(table)
                        logger.info(f"Batch {current_batch} complete - extracted {len(batch_results)} tables")
                        for page_num, table in batch_results.items():
                            if table:
                                logger.info(f"  - Page {page_num}: {len(table.rows)} rows, {len(table.headers)} columns")
                                logger.info(f"    Headers: {table.headers}")
                    else:
                        logger.error(f"Batch {current_batch} failed to process")
                except Exception as batch_error:
                    logger.error(f"Error in batch {current_batch}: {str(batch_error)}")
                    logger.error(traceback.format_exc())
                    continue
        except Exception as batch_loop_error:
            error_msg = f"Error in batch processing loop: {str(batch_loop_error)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.set_error(error_msg, "extract_tables")
            return state
            
        if not tables_data:
            error_msg = "No tables were extracted"
            logger.error(error_msg)
            state.set_error(error_msg, "extract_tables")
            return state
            
        # Update state with structured table data
        state.table_data = tables_data
        
        # Set progress to complete
        state.set_stage_progress(
            total=4,
            completed=4,
            current=f"Table extraction complete - processed {len(tables_data)} tables"
        )
        
        logger.info(f"Table extraction completed. Processed {len(tables_data)} tables")
        
        # Log completion
        log_state_change(
            state=state,
            node_name="extract_tables",
            change_type="complete",
            details={
                "tables_count": len(state.table_data),
                "pages_with_tables": sorted(list(set(s.page_number for s in state.page_summaries if s.has_tables)))
            }
        )
        
        # Save state
        await save_state(state, state.metadata.deck_id)
        logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        error_msg = f"Table extraction failed: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "extract_tables")
        await save_state(state, state.metadata.deck_id)
        return state 