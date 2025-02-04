"""Validator node for checking and fixing deck content."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from ..state import (
    BuilderState, 
    ValidationIssue, 
    ValidationIssues, 
    WorkflowStage,
    ValidationState,
    PageValidationHistory,
    ValidationAttempt,
    ValidationChange,
    ContentSection,
    PageContent,
    Pages
)
from ..utils.state_utils import save_state
from ..utils.logging_utils import log_state_change, log_error
from ...utils.llm_utils import get_llm
from ..prompts.validator_prompts import (
    VALIDATOR_SYSTEM_PROMPT,
    VALIDATOR_ANALYSIS_PROMPT,
    VALIDATOR_HISTORY_CONTEXT,
    VALIDATOR_IMPROVEMENT_PROMPT
)
from langchain.prompts import ChatPromptTemplate

# Set up logging
logger = logging.getLogger(__name__)

def create_structured_pages(slides_content: str, script_content: str) -> Pages:
    """Create structured pages from slides and script content.
    
    Args:
        slides_content: Raw slides markdown content
        script_content: Raw script markdown content
        
    Returns:
        Pages object containing structured page content
    """
    try:
        # Split content into sections
        slide_sections = [s.strip() for s in slides_content.split("---") if s.strip()]
        script_sections = [s.strip() for s in script_content.split("----") if s.strip()]
        
        # Create pages list
        pages = []
        
        # Process each section
        for i, (slide, script) in enumerate(zip(slide_sections, script_sections)):
            # Extract slide header and content
            slide_lines = slide.split("\n")
            slide_header = next((line for line in slide_lines if line.startswith("#")), f"Slide {i + 1}")
            slide_content = "\n".join(line for line in slide_lines if not line.startswith("#"))
            
            # Extract script header and content
            script_lines = script.split("\n")
            script_header = script_lines[0] if script_lines else f"Script {i + 1}"
            script_content = "\n".join(script_lines[1:]) if len(script_lines) > 1 else ""
            
            # Create page content
            page = PageContent(
                slide=ContentSection(header=slide_header.strip(), content=slide_content.strip()),
                script=ContentSection(header=script_header.strip(), content=script_content.strip())
            )
            pages.append(page)
            
        return Pages(pages=pages)
        
    except Exception as e:
        logger.error(f"Error creating structured pages: {str(e)}")
        return Pages(pages=[])

async def validate_page(
    page: PageContent,
    page_number: int,
    history: Optional[PageValidationHistory] = None
) -> ValidationIssues:
    """Validate a single page's content.
    
    Args:
        page: Page content containing slide and script
        page_number: Index of the page
        history: Optional validation history for this page
        
    Returns:
        ValidationIssues containing any found issues
    """
    try:
        # Create prompt with page content
        analysis_prompt = VALIDATOR_ANALYSIS_PROMPT.format(
            page_number=page_number,
            slide_header=page.slide.header,
            slide_content=page.slide.content,
            script_header=page.script.header,
            script_content=page.script.content
        )
        
        # Add history context if available
        if history and (history.attempts or history.changes):
            history_context = VALIDATOR_HISTORY_CONTEXT.format(
                validation_history="\n".join(f"- {a.result}" for a in history.attempts),
                change_history="\n".join(f"- {c.description}" for c in history.changes)
            )
            analysis_prompt = f"{analysis_prompt}\n\n{history_context}"
        
        # Create the full prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", VALIDATOR_SYSTEM_PROMPT),
            ("human", analysis_prompt)
        ])
        
        # Get LLM response using chain
        llm = await get_llm(temperature=0.2)
        chain = prompt | llm
        response = await chain.ainvoke({})
        
        # Parse response for issues
        validation_issues = ValidationIssues()
        
        # Add to history if provided
        if history:
            history.attempts.append(ValidationAttempt(
                attempt=len(history.attempts) + 1,
                result=response.content
            ))
        
        # If issues found, add improvement suggestions
        if "issue" in response.content.lower() or "improve" in response.content.lower():
            improvement_prompt = ChatPromptTemplate.from_messages([
                ("system", VALIDATOR_SYSTEM_PROMPT),
                ("human", f"{analysis_prompt}\n\n{VALIDATOR_IMPROVEMENT_PROMPT}")
            ])
            
            # Get improvement suggestions using chain
            improvement_chain = improvement_prompt | llm
            improvement_response = await improvement_chain.ainvoke({})
            
            # Add validation issues
            validation_issues.script_issues.append(
                ValidationIssue(
                    section=f"Page {page_number} - Script",
                    issue=response.content,
                    severity="medium",
                    suggestions=improvement_response.content.split("\n")
                )
            )
            
            validation_issues.slide_issues.append(
                ValidationIssue(
                    section=f"Page {page_number} - Slide",
                    issue=response.content,
                    severity="medium",
                    suggestions=improvement_response.content.split("\n")
                )
            )
            
        return validation_issues
        
    except Exception as e:
        logger.error(f"Error validating page {page_number}: {str(e)}")
        return ValidationIssues(
            script_issues=[
                ValidationIssue(
                    section=f"Page {page_number}",
                    issue=f"Validation failed: {str(e)}",
                    severity="high",
                    suggestions=["Check content format", "Verify required fields"]
                )
            ]
        )

async def reconstruct_content(pages: List[Dict]) -> Tuple[str, str]:
    """Reconstruct full slides and script content from validated pages.
    
    Args:
        pages: List of validated page dictionaries
        
    Returns:
        Tuple of (slides_content, script_content)
    """
    slides_content = []
    script_content = []
    
    for page in pages:
        # Add slide content with proper separators
        if page["slide"]["header"]:
            slides_content.append(f"---\n{page['slide']['header']}\n---")
        slides_content.append(page["slide"]["content"])
        
        # Add script content with proper separators
        script_header = page["script"]["header"].strip()
        script_content.append(f"---- {script_header} ----\n\n{page['script']['content']}")
    
    return "\n\n".join(slides_content), "\n\n".join(script_content)

async def save_final_content(state: BuilderState) -> bool:
    """Save the final validated content to files.
    
    Args:
        state: Current builder state
        
    Returns:
        bool indicating success
    """
    try:
        if not state.deck_info or not state.deck_info.path:
            logger.error("Missing deck info or path")
            return False
            
        # Reconstruct full content from pages
        slides_content, script_content = await reconstruct_content(
            [page.dict() for page in state.structured_pages.pages]
        )
        
        # Save slides
        slides_path = Path(state.deck_info.path) / "slides.md"
        slides_path.write_text(slides_content)
        logger.info(f"Saved final slides to {slides_path}")
        
        # Save script
        script_dir = Path(state.deck_info.path) / "audio"
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / "audio_script.md"
        script_path.write_text(script_content)
        logger.info(f"Saved final script to {script_path}")
        
        # Update state with final content
        state.slides = slides_content
        state.script = script_content
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving final content: {str(e)}")
        return False

async def validate(state: BuilderState) -> BuilderState:
    """Validate and fix deck content.
    
    Args:
        state: Current builder state
        
    Returns:
        Updated builder state
    """
    try:
        logger.info("Starting validation")
        
        # Validate required state attributes
        if not state.metadata or not state.metadata.deck_id:
            logger.error("Missing deck ID in metadata")
            state.set_error("Missing deck ID", "validate")
            return state
            
        # Get paths
        if not state.deck_info or not state.deck_info.path:
            logger.error("Missing deck info or path")
            state.set_error("Missing deck info", "validate")
            return state
            
        deck_dir = Path(state.deck_info.path)
        slides_path = deck_dir / "slides.md"
        script_path = deck_dir / "audio" / "audio_script.md"
        
        # Check if files exist
        if not slides_path.exists():
            logger.error("Slides file not found")
            state.set_error("Slides file not found", "validate")
            return state
            
        if not script_path.exists():
            logger.error("Script file not found")
            state.set_error("Script file not found", "validate")
            return state
            
        # Read content
        try:
            slides_content = slides_path.read_text()
            script_content = script_path.read_text()
        except Exception as e:
            logger.error(f"Error reading files: {str(e)}")
            state.set_error(f"Error reading files: {str(e)}", "validate")
            return state
            
        # Create structured pages if not present
        if not state.structured_pages or not state.structured_pages.pages:
            logger.info("Creating structured pages from content")
            state.structured_pages = create_structured_pages(slides_content, script_content)
            
        # Initialize validation state if not present
        if not state.validation_state:
            state.validation_state = ValidationState()
            
        # Increment attempt counter
        state.validation_state.current_attempt += 1
        
        # Validate each page
        if not state.structured_pages or not state.structured_pages.pages:
            logger.error("No structured pages found after creation")
            state.set_error("No structured pages found", "validate")
            return state
            
        for i, page in enumerate(state.structured_pages.pages, 1):
            # Get validation history for this page
            history = state.validation_state.page_histories.get(i)
            if not history:
                history = PageValidationHistory(page_number=i)
                state.validation_state.page_histories[i] = history
                
            # Validate page
            validation_issues = await validate_page(page, i, history)
            
            # Add any issues found
            if validation_issues.script_issues or validation_issues.slide_issues:
                if not state.validation_issues:
                    state.validation_issues = ValidationIssues()
                state.validation_issues.script_issues.extend(validation_issues.script_issues)
                state.validation_issues.slide_issues.extend(validation_issues.slide_issues)
                state.validation_state.invalid_pages.append(i)
        
        # If no issues found, move to next stage
        if not state.validation_issues or (
            not state.validation_issues.script_issues and 
            not state.validation_issues.slide_issues
        ):
            state.update_stage(WorkflowStage.VALIDATE)
            save_state(state, state.metadata.deck_id)
            log_state_change(state, "validate", "complete")
            
        return state
            
    except Exception as e:
        logger.error(f"Error in validate: {str(e)}")
        state.set_error(str(e), "validate")
        return state 