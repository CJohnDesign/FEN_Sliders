"""Process summaries node for analyzing slide content."""
import logging
import json
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import BuilderState, PageMetadata, PageSummary, WorkflowStage, TableDetails
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..prompts.summary_prompts import PROCESS_SUMMARIES_PROMPT
from langsmith.run_helpers import traceable
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class SummaryResult(BaseModel):
    """Model for summary generation results."""
    page_title: str = Field(default="")
    summary: str = Field(default="")
    tableDetails: Dict[str, bool] = Field(default_factory=lambda: {
        "hasBenefitsTable": False,
        "hasLimitations": False
    })
    
    model_config = ConfigDict(
        extra='ignore',
        validate_assignment=True,
        str_strip_whitespace=True
    )

class ProcessingState(BaseModel):
    """Model for tracking summary processing state."""
    total_pages: int = Field(default=0)
    processed_pages: int = Field(default=0)
    current_page: Optional[int] = Field(default=None)
    errors: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(
        extra='ignore',
        validate_assignment=True
    )

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
    if state.workflow_progress.current_stage == current:
        state.update_stage(next_stage)
        logger.info(f"Transitioned from {current} to {next_stage}")

@traceable(name="process_single_summary")
async def process_single_summary(
    metadata: PageMetadata,
    existing_summaries: Dict[int, PageSummary] = None
) -> Optional[PageSummary]:
    """Process a single page summary."""
    try:
        # Check if summary already exists and is not empty
        if (existing_summaries and 
            metadata.page_number in existing_summaries and
            existing_summaries[metadata.page_number].summary.strip() and  # Has non-empty summary
            existing_summaries[metadata.page_number].key_points):  # Has key points
            logger.info(f"Using existing summary for page {metadata.page_number}")
            return existing_summaries[metadata.page_number]
            
        # Skip if no content
        if not metadata.content:
            logger.warning(f"No content found for page {metadata.page_number}, skipping")
            return None
            
        # Create system message with imported prompt
        system_message = SystemMessage(content=PROCESS_SUMMARIES_PROMPT)
        
        # Create human message with more explicit instructions
        human_message = HumanMessage(content=f"""Please analyze this page in detail:

Page Number: {metadata.page_number}
Page Name: {metadata.page_name}
Title: {metadata.descriptive_title}

Content: {metadata.content}

You MUST provide:
1. A detailed multi-paragraph summary of all content
2. At least 3-5 specific key points about features and benefits
3. Clear action items or next steps
4. Explicitly identify if this page contains any benefits tables or plan comparisons
5. Note any limitations, restrictions, or exclusions

Pay special attention to:
- Tables comparing different plans or benefits
- Coverage details and limits
- Cost structures and tiers
- Special provisions or requirements

Your response must be a valid JSON object with all fields populated.""")
        
        # Create and execute chain with better error handling
        prompt = ChatPromptTemplate.from_messages([system_message, human_message])
        llm = await get_llm(temperature=0.2, response_format={"type": "json_object"})
        
        # Generate summary with retries
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = await llm.ainvoke(prompt.format_messages(content=metadata.content))
                parsed_response = json.loads(response.content)
                
                # Validate response has required fields and structure
                required_fields = ["page_title", "summary", "tableDetails"]
                if not all(field in parsed_response for field in required_fields):
                    raise ValueError(f"Missing required fields. Got: {list(parsed_response.keys())}")
                
                # Validate tableDetails structure
                table_details = parsed_response.get("tableDetails", {})
                if not isinstance(table_details, dict) or not all(key in table_details for key in ["hasBenefitsTable", "hasLimitations"]):
                    raise ValueError("Invalid tableDetails structure. Must contain hasBenefitsTable and hasLimitations")
                
                # Validate field types
                if not isinstance(parsed_response["page_title"], str):
                    raise ValueError("page_title must be a string")
                if not isinstance(parsed_response["summary"], str):
                    raise ValueError("summary must be a string")
                if not all(isinstance(x, bool) for x in table_details.values()):
                    raise ValueError("tableDetails values must be boolean")
                
                # Create summary object
                summary = PageSummary(
                    page_number=metadata.page_number,
                    page_name=metadata.page_name,
                    title=parsed_response["page_title"],
                    file_path=metadata.file_path,
                    summary=parsed_response["summary"],
                    key_points=[],  # No longer needed
                    action_items=[],  # No longer needed
                    has_tables=table_details["hasBenefitsTable"],
                    has_limitations=table_details["hasLimitations"]
                )
                
                # Validate summary has content
                if not summary.summary.strip():
                    if attempt < max_retries:
                        logger.warning(f"Empty summary for page {metadata.page_number}, attempt {attempt + 1}")
                        continue
                    else:
                        raise ValueError("Failed to generate non-empty summary after retries")
                        
                logger.info(f"Generated summary for page {metadata.page_number}")
                return summary
                
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    logger.warning(f"JSON parse error on attempt {attempt + 1}: {str(e)}")
                    continue
                else:
                    logger.error(f"Failed to parse JSON response after {max_retries} retries")
                    return None
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Error on attempt {attempt + 1}: {str(e)}")
                    continue
                else:
                    logger.error(f"Failed after {max_retries} retries: {str(e)}")
                    return None
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing summary for page {metadata.page_number}: {str(e)}")
        return None

@traceable(name="process_summaries")
async def process_summaries(state: BuilderState) -> BuilderState:
    """Process summaries for each page."""
    logger.info("Starting summary processing")
    
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
    
    processing_state = ProcessingState(
        total_pages=len(state.page_metadata) if state.page_metadata else 0
    )
    
    for idx, page_meta in enumerate(state.page_metadata or []):
        try:
            processing_state.current_page = idx + 1
            logger.info(f"Processing page {idx + 1} of {processing_state.total_pages}")
            
            # Process summary using existing process_single_summary function
            summary = await process_single_summary(
                page_meta,
                {meta.page_number: meta for meta in state.page_summaries.values()} if state.page_summaries else None
            )
            
            if summary:
                # Store in state using page number as key
                state.page_summaries[idx + 1] = summary
                processing_state.processed_pages += 1
            
        except Exception as e:
            error_msg = f"Error processing page {idx + 1}: {str(e)}"
            logger.error(error_msg)
            processing_state.errors.append(error_msg)
    
    logger.info(f"Completed summary processing. Processed {processing_state.processed_pages} pages with {len(processing_state.errors)} errors")
    
    # Save state after processing
    await save_state(state, state.metadata.deck_id)
    
    return state

async def process_single_page(page_metadata: PageMetadata, state: BuilderState) -> Optional[PageSummary]:
    """Process a single page to generate its summary."""
    try:
        # Create page summary with page name from metadata
        summary = await process_single_summary(page_metadata)
        if summary:
            return PageSummary(
                page_number=page_metadata.page_number,
                page_name=page_metadata.page_name,
                title=summary.title,
                summary=summary.summary,
                key_points=summary.key_points,
                action_items=summary.action_items,
                has_tables=summary.has_tables,
                has_limitations=summary.has_limitations
            )
        return None
        
    except Exception as e:
        logger.error(f"Failed to process page {page_metadata.page_number}: {str(e)}")
        return None 