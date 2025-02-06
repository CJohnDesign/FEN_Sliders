"""Aggregate summary node for combining all content."""
import logging
from typing import Dict, Any, List
from pathlib import Path
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, WorkflowStage, WorkflowProgress, StageProgress
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..prompts.summary_prompts import AGGREGATE_SUMMARY_PROMPT
from datetime import datetime
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

@traceable(name="aggregate_summary")
async def aggregate_summary(state: BuilderState) -> BuilderState:
    """Aggregate all content summaries and prepare for slide generation."""
    try:
        logger.info("Starting summary aggregation")
        
        # Initialize workflow progress if not present
        if not state.workflow_progress:
            state.workflow_progress = WorkflowProgress(
                current_stage=WorkflowStage.PROCESS,
                stages={
                    WorkflowStage.PROCESS: StageProgress(
                        status="in_progress",
                        started_at=datetime.now().isoformat()
                    )
                }
            )
        
        # Verify we're in the correct stage
        if state.workflow_progress.current_stage != WorkflowStage.PROCESS:
            logger.warning(f"Expected stage {WorkflowStage.PROCESS}, got {state.workflow_progress.current_stage}")
            state.update_stage(WorkflowStage.PROCESS)
            
        # Validate input state
        if not state.page_summaries:
            logger.error("No page summaries found in state")
            state.set_error(
                "Missing required content",
                "aggregate_summary",
                {"missing": ["page_summaries"]}
            )
            return state
            
        # Combine summaries with table data
        aggregated_content = []
        for summary in state.page_summaries:
            content = {
                "page_number": summary.page_number,
                "title": summary.page_name,
                "summary": summary.summary,
                "key_points": summary.key_points,
                "action_items": summary.action_items,
                "has_tables": summary.has_tables,
                "has_limitations": summary.has_limitations
            }
            
            # Add table data if available
            if summary.has_tables and state.table_data:
                # Find matching table data for this page
                page_tables = [table for table in state.table_data if table.metadata.get("page_number") == str(summary.page_number)]
                if page_tables:
                    content["tables"] = page_tables
                    
            aggregated_content.append(content)
            
        # Sort by page number
        aggregated_content.sort(key=lambda x: x["page_number"])
        
        # Update state with aggregated content
        state.aggregated_content = aggregated_content
        
        # Create processed summaries string for slide generation
        processed_summaries = ""
        for content in aggregated_content:
            processed_summaries += f"\n## {content['title']}\n\n"
            processed_summaries += f"{content['summary']}\n\n"
            if content.get("key_points"):
                processed_summaries += "**Key Points:**\n"
                for point in content["key_points"]:
                    processed_summaries += f"- {point}\n"
                processed_summaries += "\n"
            if content.get("action_items"):
                processed_summaries += "**Action Items:**\n"
                for item in content["action_items"]:
                    processed_summaries += f"- {item}\n"
                processed_summaries += "\n"
            if content.get("tables"):
                processed_summaries += "**Tables:**\n"
                for table in content["tables"]:
                    processed_summaries += f"- Headers: {', '.join(table.headers)}\n"
                    for row in table.rows:
                        processed_summaries += f"  - {', '.join(row)}\n"
                processed_summaries += "\n"
        
        # Update state with processed summaries
        state.processed_summaries = processed_summaries
        
        # Log completion
        log_state_change(
            state=state,
            node_name="aggregate_summary",
            change_type="complete",
            details={
                "pages_processed": len(aggregated_content),
                "pages_with_tables": len([c for c in aggregated_content if c.get("has_tables", False)]),
                "processed_summaries_length": len(processed_summaries)
            }
        )
        
        # Update workflow stage
        state.update_stage(WorkflowStage.PROCESS_SLIDES)
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
            
        return state
        
    except Exception as e:
        error_msg = f"Error during summary aggregation: {str(e)}"
        logger.error(error_msg)
        state.set_error(error_msg, "aggregate_summary")
        return state 