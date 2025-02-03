"""Table extraction node for processing tables in slides."""
import logging
import os
import base64
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from ..state import BuilderState, TableData, PageMetadata, PageSummary
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm

# Set up logging
logger = logging.getLogger(__name__)

BATCH_SIZE = 5

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def create_table_chain():
    """Create the chain for extracting table data."""
    # Use centralized LLM configuration
    llm = await get_llm(
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at analyzing presentation slides and extracting tabular data.
                     Focus on identifying and structuring:
                     1. Plan tiers and their features
                     2. Benefit comparisons
                     3. Coverage limits
                     4. Pricing information
                     
                     Output must be a valid JSON object with this structure:
                     {
                         "headers": ["Column1", "Column2", ...],
                         "rows": [
                             ["Row1Col1", "Row1Col2", ...],
                             ["Row2Col1", "Row2Col2", ...]
                         ],
                         "table_type": "benefits",
                         "metadata": {}
                     }"""),
        ("human", [
            {"type": "text", "text": "Please extract any tables from this slide."},
            {"type": "image_url", "image_url": "{image_data}"}
        ])
    ])
    
    # Create chain that runs synchronously
    chain = prompt | llm
    
    return chain

async def process_page_batch(
    batch: List[Tuple[PageSummary, str]], 
    chain,
    state: BuilderState
) -> Dict[int, Dict]:
    """Process a batch of pages concurrently."""
    async def process_single_page(summary: PageSummary, image_path: str) -> Tuple[int, Dict]:
        try:
            if not os.path.exists(image_path):
                logger.warning(f"Image not found at path: {image_path} for page {summary.page_number}")
                return summary.page_number, None
                
            # Encode image
            image_data = encode_image_to_base64(image_path)
                
            # Extract table data
            response = await chain.ainvoke({"image_data": image_data})
            
            # Parse JSON response
            result = json.loads(response.content)
            
            # Log progress
            log_state_change(
                state=state,
                node_name="extract_tables",
                change_type="table_extracted",
                details={
                    "page_number": summary.page_number,
                    "file_path": image_path
                }
            )
            
            return summary.page_number, result
            
        except Exception as e:
            logger.error(f"Error processing table on page {summary.page_number}: {str(e)}")
            return summary.page_number, None

    # Process batch concurrently
    tasks = [process_single_page(summary, image_path) for summary, image_path in batch]
    results = await asyncio.gather(*tasks)
    
    # Filter out failed results and convert to dict
    return {page_num: data for page_num, data in results if data is not None}

async def extract_tables(state: BuilderState) -> BuilderState:
    """Extract tables from pages."""
    try:
        # Get pages with tables
        pages_with_tables = []
        
        # First, create a mapping of page numbers to file paths from metadata
        page_paths = {
            meta.page_number: meta.file_path 
            for meta in state.page_metadata
        }
        
        # Then get summaries with tables and their corresponding file paths
        if state.page_summaries:
            for summary in state.page_summaries:
                if summary.has_tables and summary.page_number in page_paths:
                    pages_with_tables.append((summary, page_paths[summary.page_number]))
                else:
                    if summary.has_tables:
                        logger.warning(f"Page {summary.page_number} has tables but no corresponding file path found")
                    
        if not pages_with_tables:
            logger.info("No pages with tables found")
            return state
            
        # Create table chain
        chain = await create_table_chain()
        
        # Process pages in batches
        tables_data = {}
        for i in range(0, len(pages_with_tables), BATCH_SIZE):
            batch = pages_with_tables[i:i + BATCH_SIZE]
            logger.info(f"Processing batch {i//BATCH_SIZE + 1} of {(len(pages_with_tables) + BATCH_SIZE - 1)//BATCH_SIZE}")
            
            batch_results = await process_page_batch(batch, chain, state)
            tables_data.update(batch_results)
            
        # Update state
        state.tables_data = tables_data
        
        # Log completion
        log_state_change(
            state=state,
            node_name="extract_tables",
            change_type="complete",
            details={"total_tables": len(tables_data)}
        )
        
        return state
        
    except Exception as e:
        log_error(state, "extract_tables", e)
        state.error_context = {
            "error": str(e),
            "stage": "table_extraction"
        }
        return state 