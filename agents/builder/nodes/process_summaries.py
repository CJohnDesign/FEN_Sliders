"""Process summaries node for analyzing slide content."""
import logging
import json
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, PageMetadata, PageSummary, WorkflowStage
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..prompts.summary_prompts import PROCESS_SUMMARIES_PROMPT

# Set up logging
logger = logging.getLogger(__name__)

def preserve_state(state: BuilderState, field_name: str) -> Any:
    """Helper to preserve state fields."""
    return getattr(state, field_name, None)

def update_state(state: BuilderState, field_name: str, new_value: Any) -> None:
    """Helper to safely update state fields."""
    if not getattr(state, field_name, None):
        setattr(state, field_name, new_value)
        logger.info(f"Updated state field: {field_name}")

def transition_stage(state: BuilderState, current: WorkflowStage, next_stage: WorkflowStage) -> None:
    """Helper for stage transitions."""
    if state.current_stage == current:
        state.update_stage(next_stage)
        save_state(state, state.metadata.deck_id)
        log_state_change(state, current.value, "complete")
        logger.info(f"Transitioned from {current} to {next_stage}")

async def process_single_summary(
    metadata: PageMetadata,
    existing_summaries: Dict[int, PageSummary] = None
) -> Optional[PageSummary]:
    """Process a single page summary."""
    try:
        # Check if summary already exists
        if existing_summaries and metadata.page_number in existing_summaries:
            logger.info(f"Using existing summary for page {metadata.page_number}")
            return existing_summaries[metadata.page_number]
            
        # Skip if no content
        if not metadata.content:
            logger.warning(f"No content found for page {metadata.page_number}, skipping")
            return None
            
        # Create system message with imported prompt
        system_message = SystemMessage(content=PROCESS_SUMMARIES_PROMPT)
        
        # Create human message for this page
        human_message = HumanMessage(content=f"""Please analyze and summarize this page:

Page {metadata.page_number}: {metadata.page_name}

Content: {metadata.content}

Please provide:
1. A concise summary
2. Key points
3. Any action items
4. Note if there are any tables
5. Note if there are any limitations or restrictions""")
        
        # Create and execute chain
        prompt = ChatPromptTemplate.from_messages([system_message, human_message])
        llm = await get_llm(temperature=0.2)
        chain = prompt | llm
        
        # Generate summary
        response = await chain.ainvoke({})
        
        # Parse response
        try:
            result = json.loads(response.content)
        except:
            # If not JSON, treat entire response as summary
            result = {
                "summary": response.content.strip(),
                "key_points": [],
                "action_items": [],
                "has_tables": "table" in response.content.lower(),
                "has_limitations": "limit" in response.content.lower() or "restrict" in response.content.lower()
            }
        
        # Create summary object
        summary = PageSummary(
            page_number=metadata.page_number,
            page_name=metadata.page_name,
            file_path=metadata.file_path,
            summary=result.get("summary", ""),
            key_points=result.get("key_points", []),
            action_items=result.get("action_items", []),
            has_tables=result.get("has_tables", False),
            has_limitations=result.get("has_limitations", False)
        )
        
        logger.info(f"Generated summary for page {metadata.page_number}")
        return summary
        
    except Exception as e:
        logger.error(f"Error processing summary for page {metadata.page_number}: {str(e)}")
        return None

async def process_summaries(state: BuilderState) -> BuilderState:
    """Process summaries for all pages while preserving existing state."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.PROCESS_SUMMARIES:
            logger.warning(f"Expected stage {WorkflowStage.PROCESS_SUMMARIES}, but got {state.current_stage}")
            
        # Preserve existing state
        existing_summaries = {
            summary.page_number: summary 
            for summary in (preserve_state(state, "page_summaries") or [])
        }
            
        if not state.deck_info or not state.deck_info.path:
            logger.error("Missing deck_info in state")
            state.set_error("Missing deck info", "process_summaries")
            return state
            
        # Check for required state
        if not state.page_metadata:
            logger.error("No page metadata found in state")
            state.set_error("No page metadata available", "process_summaries")
            return state
            
        logger.info(f"Processing summaries for {len(state.page_metadata)} pages")
        
        # Process each page
        processed_summaries = []
        for metadata in sorted(state.page_metadata, key=lambda x: x.page_number):
            summary = await process_single_summary(metadata, existing_summaries)
            if summary:
                processed_summaries.append(summary)
                
        # Update state with processed summaries
        state.page_summaries = processed_summaries
        
        # Log completion and transition stage
        log_state_change(
            state=state,
            node_name="process_summaries",
            change_type="complete",
            details={
                "processed_summaries": len(processed_summaries),
                "deck_id": state.metadata.deck_id
            }
        )
        
        # Move to next stage
        transition_stage(state, WorkflowStage.PROCESS_SUMMARIES, WorkflowStage.EXTRACT_TABLES)
        logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        error_msg = f"Summary processing failed: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "process_summaries")
        return state 