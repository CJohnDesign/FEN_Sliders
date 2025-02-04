"""Validation node for checking deck content."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from string import Template
from pydantic import BaseModel, Field
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from ..state import BuilderState, ValidationIssue, ValidationIssues, ValidationResult, WorkflowStage
from ..prompts.validator_prompts import VALIDATION_PROMPT
from ..utils.logging_utils import log_state_change, log_error, log_validation
from ..config.models import get_model_config
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
import json
import os
import re
from openai import AsyncOpenAI
from langsmith.run_helpers import traceable
from ...utils.content import save_content
from ..utils.content_parser import Section, parse_script_sections, parse_slides_sections, update_state_with_content
from .script_writer import script_writer, escape_curly_braces
from .slides_writer import slides_writer

# Set up logging
logger = logging.getLogger(__name__)

class ValidationResult(BaseModel):
    """Validation result from LLM."""
    is_valid: bool
    validation_issues: ValidationIssues = Field(default_factory=ValidationIssues)
    suggested_fixes: Optional[Dict[str, str]] = Field(default_factory=dict)

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
        
        # Format content as a string with sections
        content_sections = []
        if hasattr(state, 'slides') and state.slides:
            content_sections.append("# Slides:\n" + escape_curly_braces(state.slides))
        if hasattr(state, 'script') and state.script:
            content_sections.append("# Script:\n" + escape_curly_braces(state.script))
        if hasattr(state, 'metadata') and state.metadata:
            content_sections.append("# Metadata:\n" + escape_curly_braces(str(state.metadata.model_dump())))
            
        # Join sections with clear separators
        content = "\n\n---\n\n".join(content_sections)
        
        # Run validation with properly formatted content
        result = await chain.ainvoke({"content": content})
        
        # Convert to proper Pydantic model
        validation_result = ValidationResult(
            is_valid=result.is_valid,
            validation_issues=ValidationIssues(
                script_issues=[ValidationIssue(**issue) for issue in result.validation_issues.script_issues],
                slide_issues=[ValidationIssue(**issue) for issue in result.validation_issues.slide_issues]
            ),
            suggested_fixes=result.suggested_fixes or {}
        )
        
        return validation_result
        
    except Exception as e:
        log_error(state, "validate_content", e)
        # Return failed validation with more specific error information
        return ValidationResult(
            is_valid=False,
            validation_issues=ValidationIssues(
                script_issues=[
                    ValidationIssue(
                        section="validation",
                        issue=f"Validation failed: {str(e)}",
                        severity="high",
                        suggestions=["Check if all required content is present", "Verify content format"]
                    )
                ],
                slide_issues=[]
            ),
            suggested_fixes={}
        )

async def apply_fixes(state: BuilderState, suggested_fixes: Dict[str, str]) -> BuilderState:
    """Apply suggested fixes to content."""
    try:
        logger.info("Applying fixes to content...")
        
        # Apply script fixes if present
        if "script" in suggested_fixes:
            logger.info("Applying script fixes...")
            state = await script_writer(state)
            
        # Apply slides fixes if present
        if "slides" in suggested_fixes:
            logger.info("Applying slides fixes...")
            state = await slides_writer(state)
            
        return state
        
    except Exception as e:
        log_error(state, "apply_fixes", e)
        state.error_context = {
            "error": f"Failed to apply fixes: {str(e)}",
            "stage": "validation"
        }
        return state

async def validate_and_fix(state: BuilderState) -> BuilderState:
    """Validate and fix deck content."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.VALIDATE:
            logger.warning(f"Expected stage {WorkflowStage.VALIDATE}, but got {state.current_stage}")
        
        # Initialize validation state if needed
        state.retry_count = getattr(state, 'retry_count', 0)
        state.max_retries = getattr(state, 'max_retries', 3)
            
        # Skip if no content to validate
        if not hasattr(state, 'slides') and not hasattr(state, 'script'):
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
        state.validation_issues = validation_result.validation_issues
        
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
                    "issues": validation_result.validation_issues.model_dump()
                }
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="validate",
            change_type="complete",
            details={
                "validation_issues": len(validation_result.validation_issues.script_issues) + len(validation_result.validation_issues.slide_issues),
                "needs_fixes": state.needs_fixes,
                "retry_count": state.retry_count
            }
        )
        
        # Update workflow stage
        state.current_stage = WorkflowStage.VALIDATE
        logger.info(f"Moving to next stage: {state.current_stage}")
        
        # Save state
        if hasattr(state, 'metadata') and state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "validate_and_fix", e)
        state.error_context = {
            "error": f"Validation failed: {str(e)}",
            "stage": "validation"
        }
        return state

async def validate_sync(state: BuilderState) -> BuilderState:
    """Validate and fix slide-script synchronization."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.VALIDATE:
            logger.warning(f"Expected stage {WorkflowStage.VALIDATE}, but got {state.current_stage}")
        
        # Initialize validation state if needed
        state.retry_count = getattr(state, 'retry_count', 0)
        state.max_retries = getattr(state, 'max_retries', 3)
            
        # Skip if no content to validate
        if not hasattr(state, 'slides') or not hasattr(state, 'script'):
            logger.info("No content to validate")
            state.error_context = {
                "error": "No content available for validation",
                "stage": "validation"
            }
            return state
            
        # Parse script and slides sections
        script_sections = parse_script_sections(state.script)
        slides_sections = parse_slides_sections(state.slides)

        # Create message template
        message_template = Template('''Validate these sections and return a JSON response:
                
SCRIPT SECTIONS:
$script_sections

SLIDES SECTIONS:
$slides_sections''')

        # Create messages for validation
        messages = [
            {
                "role": "system",
                "content": VALIDATION_PROMPT
            },
            {
                "role": "user",
                "content": message_template.substitute(
                    script_sections=escape_curly_braces(json.dumps([s for s in script_sections], indent=2) if script_sections else "No script sections"),
                    slides_sections=escape_curly_braces(json.dumps([s for s in slides_sections], indent=2) if slides_sections else "No slides sections")
                )
            }
        ]

        # Run validation with properly formatted content
        result = await validate_content(state)
        
        # Update state with validation results
        state.needs_fixes = not result.is_valid
        state.validation_issues = result.validation_issues
        
        # Apply fixes if needed and available
        if state.needs_fixes and result.suggested_fixes:
            logger.info("Applying suggested fixes...")
            state = await apply_fixes(state, result.suggested_fixes)
            state.retry_count += 1
            
            # Check if we've hit max retries
            if state.retry_count >= state.max_retries:
                logger.warning(f"Hit max retries ({state.max_retries})")
                state.error_context = {
                    "error": "Max validation retries reached",
                    "stage": "validation",
                    "issues": [issue for issues in state.validation_issues.values() for issue in issues]
                }
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="validate_sync",
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
        log_error(state, "validate_sync", e)
        state.error_context = {
            "error": f"Validation sync failed: {str(e)}",
            "stage": "validation"
        }
        return state 