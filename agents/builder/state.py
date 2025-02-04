"""State management for the builder agent."""
import logging
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Set up logging
logger = logging.getLogger(__name__)

class WorkflowStage(str, Enum):
    """Enum for tracking workflow stages."""
    CREATE_DECK = "create_deck"
    PROCESS_IMAGES = "process_imgs"
    PROCESS_SUMMARIES = "process_summaries"
    EXTRACT_TABLES = "extract_tables"
    AGGREGATE_SUMMARY = "aggregate_summary"
    PROCESS_SLIDES = "process_slides"
    SETUP_AUDIO = "setup_audio"
    VALIDATE = "validate"
    COMPLETE = "complete"

class DeckInfo(BaseModel):
    """Information about the deck."""
    path: str
    template: str = "FEN_TEMPLATE"

class DeckMetadata(BaseModel):
    """Metadata for the deck."""
    deck_id: str
    title: str
    version: str = "1.0.0"
    author: str = "FirstEnroll"
    theme: str = "default"

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
    """Validation issue details."""
    type: str
    description: str
    severity: str = "medium"
    location: str
    suggestions: List[str] = Field(default_factory=list)

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

class BuilderState(BaseModel):
    """Main state container for the builder agent."""
    # Core metadata
    metadata: Optional[DeckMetadata] = None
    deck_info: Optional[DeckInfo] = None
    
    # Workflow tracking
    current_stage: WorkflowStage = WorkflowStage.CREATE_DECK
    completed_stages: List[WorkflowStage] = Field(default_factory=list)
    
    # Content state
    slides: Optional[str] = None
    script: Optional[str] = None
    audio_script: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_info: Optional[Dict[str, Any]] = None
    slide_count: Optional[int] = None
    processed_content: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Page tracking
    page_metadata: Optional[List[PageMetadata]] = None
    page_summaries: Optional[List[PageSummary]] = None
    structured_slides: Optional[List[SlideContent]] = None
    tables_data: Optional[Dict[int, TableData]] = None
    processed_summaries: Optional[str] = None  # Aggregated summary content
    
    # Processing state
    needs_fixes: bool = False
    retry_count: int = 0
    max_retries: int = 3
    validation_issues: List[ValidationIssue] = Field(default_factory=list)
    error_context: Optional[Dict[str, Any]] = None
    awaiting_input: Optional[str] = None
    
    # Communication
    messages: List[Message] = Field(default_factory=list)
    
    def update_stage(self, completed_stage: WorkflowStage) -> None:
        """Update workflow stage after completion of a node."""
        # Add to completed stages if not already there
        if completed_stage not in self.completed_stages:
            self.completed_stages.append(completed_stage)
        
        # Set next stage based on workflow order
        stage_order = list(WorkflowStage)
        try:
            current_index = stage_order.index(completed_stage)
            if current_index < len(stage_order) - 1:
                self.current_stage = stage_order[current_index + 1]
            else:
                self.current_stage = WorkflowStage.COMPLETE
        except ValueError:
            logger.error(f"Invalid stage: {completed_stage}")
    
    def add_page_metadata(self, page_data: PageMetadata) -> None:
        """Add metadata for a processed page."""
        if not self.page_metadata:
            self.page_metadata = []
            
        # Update existing or add new
        for i, metadata in enumerate(self.page_metadata):
            if metadata.page_number == page_data.page_number:
                self.page_metadata[i] = page_data
                return
                
        self.page_metadata.append(page_data)
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, str]] = None) -> None:
        """Add a message to the conversation history."""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert state to dictionary format."""
        return super().model_dump(**kwargs)

def convert_messages_to_dict(state: BuilderState) -> Dict[str, Any]:
    """Convert BuilderState to a serializable dictionary format."""
    # Use Pydantic's built-in serialization
    return state.model_dump() 