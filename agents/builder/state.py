"""State management for the builder agent."""
import logging
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

# Set up logging
logger = logging.getLogger(__name__)

class WorkflowStage(str, Enum):
    """Stages in the builder workflow."""
    # New stages
    INIT = "init"
    VALIDATE = "validate"
    GENERATE = "generate"
    REVIEW = "review"
    COMPLETE = "complete"
    
    # Legacy stages (for backward compatibility)
    CREATE_DECK = "create_deck"
    PROCESS_IMAGES = "process_imgs"
    PROCESS_SUMMARIES = "process_summaries"
    EXTRACT_TABLES = "extract_tables"
    AGGREGATE_SUMMARY = "aggregate_summary"
    PROCESS_SLIDES = "process_slides"
    SETUP_AUDIO = "setup_audio"
    GOOGLE_DRIVE_SYNC = "google_drive_sync"
    
    @classmethod
    def map_legacy_stage(cls, stage: str) -> 'WorkflowStage':
        """Map legacy stage to new stage."""
        stage_mapping = {
            "create_deck": cls.INIT,
            "process_imgs": cls.GENERATE,
            "process_summaries": cls.GENERATE,
            "extract_tables": cls.GENERATE,
            "aggregate_summary": cls.GENERATE,
            "process_slides": cls.GENERATE,
            "setup_audio": cls.GENERATE,
            "validate": cls.VALIDATE,
            "google_drive_sync": cls.COMPLETE,
            "complete": cls.COMPLETE
        }
        return stage_mapping.get(stage, cls.INIT)

class DeckInfo(BaseModel):
    """Information about the deck."""
    path: str
    template: str = "FEN_TEMPLATE"
    
    model_config = ConfigDict(
        extra='ignore'  # Allow extra fields for backward compatibility
    )

class DeckMetadata(BaseModel):
    """Metadata for a deck."""
    deck_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    model_config = ConfigDict(
        extra='ignore'  # Allow extra fields for backward compatibility
    )

class PageMetadata(BaseModel):
    """Metadata for a single page."""
    page_number: int
    page_name: str
    file_path: str
    content_type: str = "slide"

class PageSummary(BaseModel):
    """Summary of a page's content."""
    page_number: int
    page_name: str
    file_path: str
    summary: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    has_tables: bool = False
    has_limitations: bool = False

class TableData(BaseModel):
    """Structured table data."""
    headers: List[str]
    rows: List[List[str]]
    table_type: str = "benefits"
    metadata: Dict[str, str] = Field(default_factory=dict)

class ValidationIssue(BaseModel):
    """A validation issue found in the content."""
    section: str
    issue: str
    severity: str
    suggestions: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(
        extra='ignore'  # Allow extra fields for backward compatibility
    )

class ValidationIssues(BaseModel):
    """Collection of validation issues."""
    script_issues: List[ValidationIssue] = Field(default_factory=list)
    slide_issues: List[ValidationIssue] = Field(default_factory=list)
    suggested_fixes: Dict[str, str] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        extra='ignore'  # Allow extra fields for backward compatibility
    )

class ValidationResult(BaseModel):
    """Result of content validation."""
    is_valid: bool
    validation_issues: ValidationIssues = Field(default_factory=ValidationIssues)
    suggested_fixes: Optional[Dict[str, str]] = Field(default_factory=dict)

class SlideContent(BaseModel):
    """Structured slide content."""
    page_number: int
    title: str
    content: str
    has_tables: bool = False
    has_limitations: bool = False
    layout: str = "default"
    transitions: List[str] = Field(default_factory=list)

class Message(BaseModel):
    """Message for tracking agent communication."""
    role: str
    content: str
    metadata: Dict[str, str] = Field(default_factory=dict)

class GoogleDriveConfig(BaseModel):
    """Configuration for Google Drive integration."""
    credentials_path: str
    folder_id: Optional[str] = None
    pdf_folder_name: str = "Insurance PDFs"
    docs_folder_name: str = "Generated Docs"

class GoogleDriveSyncInfo(BaseModel):
    """Information about Google Drive sync status."""
    pdf_folder_id: str
    docs_folder_id: str
    uploaded_pdfs: List[Dict[str, str]]
    created_docs: List[Dict[str, str]]

class ErrorContext(BaseModel):
    """Context for errors that occur during processing."""
    error: str
    stage: str
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        extra='ignore'  # Allow extra fields for backward compatibility
    )

class BuilderState(BaseModel):
    """State for the builder agent."""
    # Core content
    slides: Optional[str] = None
    script: Optional[str] = None
    metadata: Optional[DeckMetadata] = None
    deck_info: Optional[DeckInfo] = None
    
    # NEW FIELD: Processed summaries to be used for slides generation
    processed_summaries: Optional[str] = None
    
    # Page processing state
    page_summaries: List[PageSummary] = Field(default_factory=list)
    page_metadata: List[PageMetadata] = Field(default_factory=list)
    structured_slides: List[SlideContent] = Field(default_factory=list)
    slide_count: Optional[int] = None
    
    # Table data
    table_data: List[TableData] = Field(default_factory=list)
    
    # Aggregated content
    aggregated_content: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Google Drive state
    google_drive_config: Optional[GoogleDriveConfig] = None
    google_drive_sync_info: Optional[GoogleDriveSyncInfo] = None
    
    # Workflow state
    current_stage: WorkflowStage = Field(default=WorkflowStage.INIT)
    needs_fixes: bool = Field(default=False)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    
    # Validation state
    validation_issues: Optional[ValidationIssues] = Field(default_factory=ValidationIssues)
    
    # Error handling
    error_context: Optional[ErrorContext] = None
    
    # Methods
    def update_stage(self, new_stage: WorkflowStage) -> None:
        """Update the current workflow stage."""
        self.current_stage = new_stage
    
    def add_validation_issue(self, issue: ValidationIssue, is_script: bool = True) -> None:
        """Add a validation issue to the appropriate list."""
        if not self.validation_issues:
            self.validation_issues = ValidationIssues()
        
        if is_script:
            self.validation_issues.script_issues.append(issue)
        else:
            self.validation_issues.slide_issues.append(issue)
    
    def clear_validation_issues(self) -> None:
        """Clear all validation issues."""
        self.validation_issues = ValidationIssues()
    
    def set_error(self, error: str, stage: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Set error context."""
        self.error_context = ErrorContext(
            error=error,
            stage=stage,
            details=details or {}
        )
    
    model_config = ConfigDict(
        extra='ignore',  # Allow extra fields for backward compatibility
        validate_assignment=True,  # Validate on attribute assignment
        str_strip_whitespace=True  # Strip whitespace from string values
    )

def convert_messages_to_dict(state: BuilderState) -> Dict[str, Any]:
    """Convert BuilderState to a serializable dictionary format."""
    # Use Pydantic's built-in serialization
    return state.model_dump() 