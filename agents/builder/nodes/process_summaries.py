"""Process summaries node for analyzing slide content."""
import logging
import json
import traceback
from pathlib import Path
from typing import List, Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, PageMetadata, PageSummary, WorkflowStage
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..prompts.summary_prompts import PROCESS_SUMMARIES_PROMPT

# Set up logging
logger = logging.getLogger(__name__)

async def process_summaries(state: BuilderState) -> BuilderState:
    """Process summaries for all pages."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.PROCESS_SUMMARIES:
            logger.warning(f"Expected stage {WorkflowStage.PROCESS_SUMMARIES}, but got {state.current_stage}")
            
        if not state.deck_info or not state.deck_info.path:
            logger.error("Missing deck_info in state")
            return state
            
        # Check for required state
        if not state.page_metadata:
            logger.error("No page metadata found in state")
            state.error_context = {
                "error": "No page metadata available",
                "stage": "summary_processing"
            }
            return state
            
        logger.info(f"Processing summaries for {len(state.page_metadata)} pages")
        
        # Create system message with imported prompt
        system_message = SystemMessage(content=PROCESS_SUMMARIES_PROMPT)
        
        # Process each page
        summaries = []
        for metadata in sorted(state.page_metadata, key=lambda x: x.page_number):
            try:
                # Create human message for this page
                human_message = HumanMessage(content=f"Please analyze and summarize this page:\n\nPage {metadata.page_number}: {metadata.page_name}\n\nContent: {metadata.content}")
                
                # Create and execute chain
                prompt = ChatPromptTemplate.from_messages([system_message, human_message])
                llm = await get_llm(temperature=0.2)
                chain = prompt | llm
                
                # Generate summary
                response = await chain.ainvoke({})
                
                # Create summary object
                summary = PageSummary(
                    page_number=metadata.page_number,
                    page_name=metadata.page_name,
                    summary=response.content.strip(),
                    file_path=metadata.file_path,
                    has_tables=metadata.has_tables
                )
                summaries.append(summary)
                
                logger.info(f"Generated summary for page {metadata.page_number}")
                
            except Exception as page_error:
                logger.error(f"Error processing page {metadata.page_number}: {str(page_error)}")
                continue
                
        # Update state with summaries
        state.page_summaries = summaries
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="process_summaries",
            change_type="complete",
            details={
                "summaries_count": len(state.page_summaries),
                "metadata_count": len(state.page_metadata)
            }
        )
        
        # Update workflow stage
        state.update_stage(WorkflowStage.PROCESS_SUMMARIES)
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "process_summaries", e)
        state.error_context = {
            "error": str(e),
            "stage": "summary_processing"
        }
        logger.error("Error during summary processing.", exc_info=True)
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 