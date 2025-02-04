"""Validation node for checking deck content."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from ..state import BuilderState, ValidationIssue, WorkflowStage
from ..prompts.validator_prompts import VALIDATION_PROMPT
from ..utils.logging_utils import log_state_change, log_error, log_validation
from ..config.models import get_model_config
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state

# Set up logging
logger = logging.getLogger(__name__)

class ValidationResult(BaseModel):
    """Validation result from LLM."""
    is_valid: bool
    issues: List[ValidationIssue] = []
    suggested_fixes: Optional[Dict[str, Any]] = None

async def create_validator_chain():
    """Create the chain for validating content."""
    # Use centralized LLM configuration
    llm = await get_llm(
        temperature=0.1,  # Lower temperature for validation
        response_format={"type": "json_object"}  # Ensure JSON output
    )
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_template(VALIDATION_PROMPT)
    
    # Create output parser
    parser = PydanticOutputParser(pydantic_object=ValidationResult)
    
    # Create chain
    chain = prompt | llm | parser
    
    return chain

async def validate_content(state: BuilderState) -> ValidationResult:
    """Validate deck content using LLM."""
    try:
        # Create validation chain
        chain = await create_validator_chain()
        
        # Prepare content for validation with proper null checks
        content = {
            "content": {
                "slides": state.slides if state.slides else "",
                "script": state.script if state.script else "",
                "metadata": state.metadata.model_dump() if state.metadata else {},
                "deck_info": state.deck_info.model_dump() if state.deck_info else {}
            }
        }
        
        # Run validation
        result = await chain.ainvoke(content)
        
        # Log validation result
        log_validation(
            state=state,
            validation_type="content",
            is_valid=result.is_valid,
            details={"issues": [issue.model_dump() for issue in result.issues] if result.issues else []}
        )
        
        return result
        
    except Exception as e:
        log_error(state, "validate_content", e)
        # Return failed validation with more specific error information
        return ValidationResult(
            is_valid=False,
            issues=[ValidationIssue(
                type="error",
                description=f"Validation failed: {str(e)}",
                severity="high",
                location="validation",
                suggestions=["Check if all required content is present", "Verify content format"]
            )]
        )

async def apply_fixes(state: BuilderState, fixes: Dict[str, Any]) -> BuilderState:
    """Apply suggested fixes to state."""
    try:
        # Apply fixes based on their type
        if "slides" in fixes:
            state.slides = fixes["slides"]
            
        if "script" in fixes:
            state.script = fixes["script"]
            
        # Log fix application
        log_validation(
            state=state,
            validation_type="fixes",
            is_valid=True,
            details={"applied_fixes": fixes}
        )
        
        return state
        
    except Exception as e:
        log_error(state, "apply_fixes", e)
        return state

async def validate_and_fix(state: BuilderState) -> BuilderState:
    """Validate and fix deck content."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.VALIDATE:
            logger.warning(f"Expected stage {WorkflowStage.VALIDATE}, but got {state.current_stage}")
        
        # Initialize validation state if needed
        if state.retry_count is None:
            state.retry_count = 0
        if state.max_retries is None:
            state.max_retries = 3
            
        # Skip if no content to validate
        if not state.slides and not state.script:
            logger.info("No content to validate")
            state.error_context = {
                "error": "No content available for validation",
                "stage": "validation"
            }
            return state
            
        # Validate content
        validation_result = await validate_content(state)
        
        # Update state with validation results
        state.needs_fixes = not validation_result.is_valid
        state.validation_issues = validation_result.issues if validation_result.issues else []
        
        # Apply fixes if needed and available
        if state.needs_fixes and validation_result.suggested_fixes:
            logger.info("Applying suggested fixes...")
            state = await apply_fixes(state, validation_result.suggested_fixes)
            state.retry_count += 1
            
            # Check if we've hit max retries
            if state.retry_count >= state.max_retries:
                logger.warning(f"Hit max retries ({state.max_retries})")
                state.error_context = {
                    "error": "Max validation retries reached",
                    "stage": "validation",
                    "issues": [issue.model_dump() for issue in state.validation_issues]
                }
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="validate",
            change_type="complete",
            details={
                "validation_issues": len(state.validation_issues),
                "needs_fixes": state.needs_fixes,
                "retry_count": state.retry_count
            }
        )
        
        # Update workflow stage
        state.update_stage(WorkflowStage.VALIDATE)
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "validate", e)
        state.error_context = {
            "error": str(e),
            "stage": "validation"
        }
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 