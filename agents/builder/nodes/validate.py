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

async def validate_single_page(
    page: PageContent,
    page_number: int,
    history: Optional[PageValidationHistory] = None
) -> Tuple[bool, ValidationIssues]:
    """Validate a single page's content.
    
    Args:
        page: Page content containing slide and script
        page_number: Index of the page
        history: Optional validation history for this page
        
    Returns:
        Tuple of (is_valid, validation_issues)
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
        
        # Get LLM response
        llm = await get_llm(temperature=0.2)
        chain = prompt | llm
        response = await chain.ainvoke({})
        
        # Parse response
        validation_result = json.loads(response.content)
        validation_issues = ValidationIssues()
        
        # Add to history if provided
        if history:
            history.attempts.append(ValidationAttempt(
                attempt=len(history.attempts) + 1,
                result=response.content
            ))
        
        # Extract issues if any
        if not validation_result["is_valid"]:
            validation_issues = ValidationIssues(**validation_result["validation_issues"])
            
        return validation_result["is_valid"], validation_issues
        
    except Exception as e:
        logger.error(f"Error validating page {page_number}: {str(e)}")
        return False, ValidationIssues(
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
        state.slides_content = slides_content
        state.script_content = script_content
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving final content: {str(e)}")
        return False

async def validate(state: BuilderState) -> BuilderState:
    """Validate deck content page by page.
    
    Args:
        state: Current builder state
        
    Returns:
        Updated builder state
    """
    try:
        logger.info("Starting validation")
        
        # Initialize validation state if not present
        if not state.validation_state:
            state.validation_state = ValidationState()
            
        # Validate required state attributes
        if not state.structured_pages or not state.structured_pages.pages:
            logger.error("Missing structured pages")
            state.set_error("Missing structured pages", "validate")
            return state
            
        # Track overall validation status
        all_valid = True
        state.validation_issues = ValidationIssues()
        
        # Validate each page
        for i, page in enumerate(state.structured_pages.pages, 1):
            # Get validation history for this page
            history = state.validation_state.page_histories.get(i)
            if not history:
                history = PageValidationHistory(page_number=i)
                state.validation_state.page_histories[i] = history
                
            # Validate page
            is_valid, issues = await validate_single_page(page, i, history)
            
            # Update overall status and collect issues
            if not is_valid:
                all_valid = False
                state.validation_issues.script_issues.extend(issues.script_issues)
                state.validation_issues.slide_issues.extend(issues.slide_issues)
                if i not in state.validation_state.invalid_pages:
                    state.validation_state.invalid_pages.append(i)
                    
            logger.info(f"Page {i} validation: {'valid' if is_valid else 'invalid'}")
        
        # Update state based on validation results
        if all_valid:
            state.update_stage(WorkflowStage.VALIDATE)
            log_state_change(state, "validate", "complete")
        else:
            log_state_change(state, "validate", "issues_found", {
                "num_script_issues": len(state.validation_issues.script_issues),
                "num_slide_issues": len(state.validation_issues.slide_issues),
                "invalid_pages": state.validation_state.invalid_pages
            })
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            await save_state(state, state.metadata.deck_id)
            
        return state
        
    except Exception as e:
        logger.error(f"Error in validate: {str(e)}")
        state.set_error(str(e), "validate")
        return state 