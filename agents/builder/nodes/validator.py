"""Validation node for checking deck content."""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from string import Template
from pydantic import BaseModel, Field, ConfigDict
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from ..state import BuilderState, ValidationIssue, ValidationIssues, WorkflowStage
from ..prompts.validator_prompts import VALIDATION_PROMPT
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..utils.state_utils import save_state
from ..utils.content_parser import parse_script_sections, parse_slides_sections
from .script_writer import escape_curly_braces
from ...utils.content import save_content
import json

# Set up logging
logger = logging.getLogger(__name__)

class ValidationResult(BaseModel):
    """Validation result from LLM."""
    is_valid: bool
    validation_issues: ValidationIssues = Field(default_factory=ValidationIssues)
    suggested_fixes: Dict[str, str] = Field(default_factory=dict)
    
    model_config = ConfigDict(extra='forbid')

async def create_validator_chain():
    """Create the chain for validating content."""
    llm = await get_llm(
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    prompt = ChatPromptTemplate.from_template(VALIDATION_PROMPT)
    parser = PydanticOutputParser(pydantic_object=ValidationResult)
    chain = prompt | llm | parser
    
    return chain

async def validate_content(state: BuilderState) -> ValidationResult:
    """Validate deck content using LLM."""
    try:
        chain = await create_validator_chain()
        
        # Format content sections
        content_sections = []
        if state.slides:
            content_sections.append("# Slides:\n" + escape_curly_braces(state.slides))
        if state.script:
            content_sections.append("# Script:\n" + escape_curly_braces(state.script))
        if state.metadata:
            content_sections.append("# Metadata:\n" + escape_curly_braces(state.metadata.model_dump_json()))
            
        # If no content to validate, return invalid result
        if not content_sections:
            return ValidationResult(
                is_valid=False,
                validation_issues=ValidationIssues(
                    script_issues=[
                        ValidationIssue(
                            section="content",
                            issue="No content available to validate",
                            severity="high",
                            suggestions=["Add slides content", "Add script content"]
                        )
                    ]
                )
            )
            
        content = "\n\n---\n\n".join(content_sections)
        logger.debug(f"Content to validate:\n{content}")
        
        try:
            result = await chain.ainvoke({"content": content})
            logger.debug(f"Raw validation result: {result}")
            
            # Convert to ValidationResult
            validation_result = ValidationResult(
                is_valid=result.is_valid,
                validation_issues=ValidationIssues(
                    script_issues=[
                        ValidationIssue(
                            section=issue.section,
                            issue=issue.issue,
                            severity=issue.severity,
                            suggestions=issue.suggestions
                        ) for issue in result.validation_issues.script_issues
                    ],
                    slide_issues=[
                        ValidationIssue(
                            section=issue.section,
                            issue=issue.issue,
                            severity=issue.severity,
                            suggestions=issue.suggestions
                        ) for issue in result.validation_issues.slide_issues
                    ]
                ),
                suggested_fixes=result.suggested_fixes or {}
            )
            
            logger.debug(f"Validation result: {validation_result.model_dump_json()}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation chain error: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return ValidationResult(
            is_valid=False,
            validation_issues=ValidationIssues(
                script_issues=[
                    ValidationIssue(
                        section="validation",
                        issue=f"Validation failed: {str(e)}",
                        severity="high",
                        suggestions=["Check content format", "Verify required fields"]
                    )
                ]
            )
        )

async def validate_and_fix(state: BuilderState) -> BuilderState:
    """Validate and fix deck content using a ReAct pattern."""
    try:
        # Initialize validation loop
        logger.info("Starting validation process")
        state.retry_count = 0  # Reset retry count at start
        
        # First check if we have required content
        if not state.slides:
            logger.warning("No slides content available - slides must be created before validation")
            state.set_error(
                "Missing required content",
                "validation",
                {"missing": ["slides"]}
            )
            return state
            
        while state.retry_count < state.max_retries:
            state.retry_count += 1
            logger.info(f"Starting validation attempt {state.retry_count}/{state.max_retries}")
            
            # Observe: Get current state through validation
            validation_result = await validate_content(state)
            logger.info(f"Validation complete. Valid: {validation_result.is_valid}")
            
            # Update state with validation results
            state.needs_fixes = not validation_result.is_valid
            state.validation_issues = validation_result.validation_issues
            
            # If content is valid, we're done
            if validation_result.is_valid:
                logger.info("Content is valid, no fixes needed")
                state.needs_fixes = False
                # Save the final valid content
                if state.deck_info and state.deck_info.path:
                    # Save slides
                    if state.slides:
                        slides_path = Path(state.deck_info.path) / "slides.md"
                        await save_content(slides_path, state.slides)
                        logger.info(f"Saved validated slides to {slides_path}")
                    
                    # Save script
                    if state.script:
                        script_path = Path(state.deck_info.path) / "audio" / "audio_script.md"
                        script_path.parent.mkdir(parents=True, exist_ok=True)
                        await save_content(script_path, state.script)
                        logger.info(f"Saved validated script to {script_path}")
                break
                
            # Think: Determine what tools to use based on issues
            tools_to_use = []
            if validation_result.validation_issues.slide_issues:
                tools_to_use.append("fix_slides")
            if validation_result.validation_issues.script_issues:
                tools_to_use.append("fix_script")
                
            if not tools_to_use:
                logger.warning("No tools selected despite validation issues")
                state.set_error(
                    "Validation failed but no tools available to fix issues",
                    "validation",
                    {"issues": validation_result.validation_issues.model_dump()}
                )
                break
                
            # Act: Apply each selected tool
            changes_made = False
            from .validator_tools import VALIDATOR_TOOLS
            
            for tool_name in tools_to_use:
                logger.info(f"Using tool: {tool_name}")
                tool = VALIDATOR_TOOLS[tool_name]
                updated_state, result = await tool(state)
                
                # Update state and track changes
                if result["success"]:
                    state = updated_state  # Update state with tool results
                    changes_made = changes_made or result["changes_made"]
                    logger.info(f"Tool {tool_name} result: {result['message']}")
                    
                    # Save the updated content after each successful tool run
                    if state.deck_info and state.deck_info.path:
                        if tool_name == "fix_slides" and state.slides:
                            slides_path = Path(state.deck_info.path) / "slides.md"
                            await save_content(slides_path, state.slides)
                            logger.info(f"Saved updated slides to {slides_path}")
                        elif tool_name == "fix_script" and state.script:
                            script_path = Path(state.deck_info.path) / "audio" / "audio_script.md"
                            script_path.parent.mkdir(parents=True, exist_ok=True)
                            await save_content(script_path, state.script)
                            logger.info(f"Saved updated script to {script_path}")
                else:
                    logger.error(f"Tool {tool_name} failed: {result['message']}")
                    state.set_error(
                        f"Tool {tool_name} failed to fix issues",
                        "validation",
                        {"tool": tool_name, "error": result["message"]}
                    )
                    break
                    
            # If no changes were made, break the loop to avoid infinite retries
            if not changes_made:
                logger.warning("No changes were made by any tools despite validation issues")
                state.set_error(
                    "Writers failed to make necessary changes",
                    "validation",
                    {"issues": state.validation_issues.model_dump()}
                )
                # Set needs_fixes to False to prevent further retries
                state.needs_fixes = False
                break
                
            logger.info("Changes made, continuing to next validation attempt")
            
        # Handle max retries
        if state.retry_count >= state.max_retries and state.needs_fixes:
            logger.error(f"Max validation attempts ({state.max_retries}) reached without success")
            state.set_error(
                "Max validation attempts reached without success",
                "validation",
                {
                    "attempts": state.retry_count,
                    "max_retries": state.max_retries,
                    "issues": state.validation_issues.model_dump() if hasattr(state, 'validation_issues') else None
                }
            )
            # Set needs_fixes to False since we're giving up
            state.needs_fixes = False
            
        # Log completion
        log_state_change(
            state=state,
            node_name="validate",
            change_type="complete",
            details={
                "validation_issues": len(state.validation_issues.script_issues) + len(state.validation_issues.slide_issues),
                "needs_fixes": state.needs_fixes,
                "retry_count": state.retry_count
            }
        )
        
        # Update stage and save
        state.update_stage(WorkflowStage.VALIDATE)
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        state.set_error(
            f"Validation process failed: {str(e)}",
            "validation"
        )
        # Set needs_fixes to False since we encountered an error
        state.needs_fixes = False
        return state 