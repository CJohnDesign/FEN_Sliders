"""Aggregate summary node for combining individual summaries into a cohesive whole."""
import logging
from typing import Any, Dict
from pathlib import Path
from langchain.prompts import ChatPromptTemplate
from ..state import BuilderState
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm

# Set up logging
logger = logging.getLogger(__name__)

async def aggregate_summary(state: BuilderState) -> BuilderState:
    """
    Aggregates individual page summaries and extracted table data into a cohesive aggregated summary.
    The summary is structured in the following sections:
      1. Cover (1 slide)
      2. Plan Overview (1 slide)
      3. Core Plan Elements (2-3 slides)
      4. Common Service Features (2-3 slides)
      5. Plan Tiers Breakdown (8-12 slides)
        A. for each tier, detail components like physician services, hospitalization details, virtual visits, prescriptions, wellness tools, and advocacy.
        B. go over each benefit in detail, piece by piece
      6. Limitations and Exclusions (1-2 slides)
      7. Key Takeaways and Action Steps (1 slide)
      8. Conclusion (1 slide)
    """
    
    logger.info("Starting aggregate summary node.")
    
    try:
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
            for page_num, table in sorted(state.tables_data.items()):
                table_str = f"Table on Page {page_num}:\n"
                table_str += "Headers: " + ", ".join(table.headers) + "\n"
                table_str += "Type: " + table.table_type + "\n"
                table_str += "Rows: " + str(len(table.rows)) + "\n"
                table_entries.append(table_str)
            extracted_tables = "\n\n".join(table_entries)
        else:
            extracted_tables = "No table data available."
        
        # Step 3: Create the LLM prompt template
        prompt_template = ChatPromptTemplate.from_template(
            """You are an expert at summarizing insurance plan data into a cohesive aggregated summary for creating presentation slides and a narrative script.
Below are the instructions for the aggregated summary structure:

1. Cover (1 slide)
   - Display the plan name and a simple tagline summarizing the plan's purpose.

2. Plan Overview (1 slide)
   - Provide a high-level summary of who the plan is for (e.g., individuals, families), what it offers (e.g., comprehensive healthcare, affordability), and the key benefits (e.g., accessibility, personal impact).

3. Core Plan Elements (2-3 slides)
   - Highlight major components like coverage areas (physician services, hospitalization, virtual visits),
     the plan structure (tiered options, co-pays, visit limits), and eligibility (individuals, families, affordability focus).

4. Common Service Features (2-3 slides)
   - Outline standard services such as provider networks, claims management, and support tools (e.g., dashboards, wellness programs, advocacy services).

5. Plan Tiers Breakdown (8-12 slides)
   - For each plan tier, detail components like physician services, hospitalization details, virtual visits, prescriptions, wellness tools, and advocacy.
   - Each tier should be detailed, but the slides should be concise and to the point.
   
6. Comparison slides showing differences among the tiers.
    - Highlight the benefits of each tier, but don't be redundant.

7. Limitations and Exclusions (1-2 slides)
   - Define exclusions (e.g., pre-existing conditions, waiting periods, prescription limitations).

8. Key Takeaways and Action Steps (1 slide)
   - Summarize the plan's flexibility, its balance between cost and coverage, and detail next steps for enrollment or obtaining support.

9. Conclusion (1 slide)
   - Conclude with a branded thank you message and final enrollment or support instructions.

Inputs:

Individual Summaries:
---------------------
{individual_summaries}

Extracted Table Information:
----------------------------
{extracted_tables}

First, outline your plan for aggregating the above information, then generate the full aggregated summary.
"""
        )
        
        try:
            # Step 4: Generate aggregated summary using a single call to the LLM
            llm = await get_llm(temperature=0.2)
            response = await llm.ainvoke(prompt_template.format(
                individual_summaries=individual_summaries,
                extracted_tables=extracted_tables
            ))
            
            aggregated_summary = response.content.strip()
            
            # Step 5: Update state with the aggregated summary
            state.processed_summaries = aggregated_summary
            
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
            
        return state
        
    except Exception as e:
        log_error(state, "aggregate_summary", e)
        state.error_context = {
            "error": str(e),
            "stage": "aggregate_summary"
        }
        logger.error("Error during summary aggregation.", exc_info=True)
        return state 