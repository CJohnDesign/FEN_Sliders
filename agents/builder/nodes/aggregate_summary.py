"""Aggregate summary node for combining individual summaries into a cohesive whole."""
import logging
from typing import Any, Dict
from pathlib import Path
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, WorkflowStage
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..prompts.summary_prompts import AGGREGATE_SUMMARY_PROMPT

# Set up logging
logger = logging.getLogger(__name__)

async def aggregate_summary(state: BuilderState) -> BuilderState:
    
    logger.info("Starting aggregate summary node.")
    
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.AGGREGATE_SUMMARY:
            logger.warning(f"Expected stage {WorkflowStage.AGGREGATE_SUMMARY}, but got {state.current_stage}")
            
        # Check for required state
        if not state.page_summaries:
            logger.error("No page summaries found in state")
            state.error_context = {
                "error": "No page summaries available",
                "stage": "aggregate_summary"
            }
            return state
            
        # Step 1: Concatenate individual summaries
        individual_summaries = "\n\n".join(
            f"Title: {summary.page_name}\nSummary: {summary.summary}"
            for summary in sorted(state.page_summaries, key=lambda x: x.page_number)
            if summary.summary
        )
        
        # Step 2: Process table data if available
        extracted_tables = ""
        if state.tables_data:
            table_entries = []
            # Create a mapping of page numbers to page names
            page_name_map = {s.page_number: s.page_name for s in state.page_summaries}
            
            for page_num, table in sorted(state.tables_data.items()):
                page_name = page_name_map.get(page_num, f"Page {page_num}")
                table_str = f"Table from: {page_name}\n"
                table_str += f"Type: {table.table_type}\n"
                # Format table as TSV
                rows = ["\t".join(table.headers)]  # Start with headers
                for row in table.rows:
                    rows.append("\t".join(str(cell) for cell in row))
                table_str += "\n".join(rows) + "\n"
                table_entries.append(table_str)
            extracted_tables = "\n\n".join(table_entries)
        else:
            extracted_tables = "No table data available."
        
        try:
            # Create prompt template using the imported prompt
            prompt_template = ChatPromptTemplate.from_template(AGGREGATE_SUMMARY_PROMPT)
            
            # Generate aggregated summary using a single call to the LLM
            llm = await get_llm(temperature=0.2)
            response = await llm.ainvoke(prompt_template.format(
                individual_summaries=individual_summaries,
                extracted_tables=extracted_tables
            ))
            
            aggregated_summary = response.content.strip()
            
            # Update state with the aggregated summary
            state.processed_summaries = aggregated_summary
            
            # Save aggregated summary as markdown file
            if state.deck_info and state.deck_info.path:
                ai_dir = Path(state.deck_info.path) / "ai"
                ai_dir.mkdir(parents=True, exist_ok=True)
                
                summary_path = ai_dir / "aggregated_summary.md"
                with open(summary_path, "w") as f:
                    f.write("# Aggregated Summary\n\n")
                    f.write(aggregated_summary)
                logger.info(f"Saved aggregated summary to {summary_path}")
            
            log_state_change(
                state=state,
                node_name="aggregate_summary",
                change_type="complete",
                details={
                    "aggregated_summary_length": len(aggregated_summary),
                    "num_summaries_processed": len(state.page_summaries),
                    "num_tables_processed": len(state.tables_data or {})
                }
            )
            logger.info("Aggregated summary generated successfully.")
            
        except Exception as llm_error:
            logger.error(f"Error during LLM processing: {str(llm_error)}")
            raise
            
        # Update workflow stage
        state.update_stage(WorkflowStage.AGGREGATE_SUMMARY)
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "aggregate_summary", e)
        state.error_context = {
            "error": str(e),
            "stage": "aggregate_summary"
        }
        logger.error("Error during summary aggregation.", exc_info=True)
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 