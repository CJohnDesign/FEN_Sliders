from typing import TypedDict, Annotated, Optional, Dict, Literal, Any, List
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from dataclasses import dataclass, asdict
import json

class PageSummary(TypedDict):
    """Structure for individual page summaries."""
    page: int
    title: str
    summary: str
    hasTable: bool
    csv: Optional[str]

@dataclass
class DeckMetadata:
    """Metadata for deck creation and configuration."""
    deck_id: str
    title: str
    template: str = "FEN_TEMPLATE"
    theme_config: dict = None

    def __post_init__(self):
        if self.theme_config is None:
            self.theme_config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key with a default fallback."""
        return getattr(self, key, default)
        
    def __getitem__(self, key: str) -> Any:
        """Support dictionary-like access."""
        return getattr(self, key)
        
    def update(self, data: Dict[str, Any]) -> None:
        """Update metadata with new values."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    def to_dict(self) -> Dict[str, Any]:
        """Convert DeckMetadata to a dictionary."""
        return {
            "deck_id": self.deck_id,
            "title": self.title,
            "template": self.template,
            "theme_config": self.theme_config
        }
        
    def json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

class BuilderState(TypedDict):
    """State management for the deck building process."""
    # Core state
    messages: Annotated[list, add_messages]  # LangGraph message history
    metadata: DeckMetadata  # Deck configuration
    
    # Deck generation state
    deck_info: Optional[Dict[str, str]]  # Path and template info
    slides: list[dict]  # Generated slide content
    
    # PDF processing state
    pdf_path: Optional[str]  # Path to uploaded PDF
    pdf_info: Optional[Dict[str, Any]]  # PDF metadata and processing info
    awaiting_input: Optional[Literal["pdf_upload"]]  # Current input requirement
    
    # Content generation state
    page_summaries: Optional[List[PageSummary]]  # List of page summaries with their metadata
    processed_summaries: Optional[str]  # Markdown formatted processed summaries
    
    # Audio state
    audio_config: Optional[dict]  # Audio generation configuration
    
    # Validation state
    needs_fixes: bool  # Whether fixes are needed
    retry_count: int  # Number of validation retries
    validation_issues: List[Dict[str, str]]  # List of validation issues
    
    # Error handling
    error_context: Optional[dict]  # Error information if any step fails 

@dataclass
class TableDetails:
    """Table details for a page."""
    hasBenefitsTable: bool
    hasLimitations: bool 

@dataclass
class PageSummary:
    page_number: int
    title: str
    content: str
    tables: List[str]
    limitations: List[str]

@dataclass
class BuilderState:
    messages: List[Dict]
    metadata: DeckMetadata
    deck_info: Optional[Dict] = None
    slides: List[Dict] = None
    script: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_info: Optional[Dict] = None
    awaiting_input: Optional[str] = None
    page_summaries: Optional[List[PageSummary]] = None
    processed_summaries: Optional[Dict] = None
    audio_config: Optional[Dict] = None
    error_context: Optional[str] = None
    needs_fixes: bool = False
    retry_count: int = 0
    validation_issues: List[str] = None

    def __post_init__(self):
        if self.slides is None:
            self.slides = []
        if self.validation_issues is None:
            self.validation_issues = []

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key with a default fallback."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        """Support dictionary-like access."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Support dictionary-like assignment."""
        setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert BuilderState to a dictionary."""
        return {
            "messages": self.messages,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "deck_info": self.deck_info,
            "slides": self.slides,
            "script": self.script,
            "pdf_path": self.pdf_path,
            "pdf_info": self.pdf_info,
            "awaiting_input": self.awaiting_input,
            "page_summaries": [asdict(s) for s in self.page_summaries] if self.page_summaries else None,
            "processed_summaries": self.processed_summaries,
            "audio_config": self.audio_config,
            "error_context": self.error_context,
            "needs_fixes": self.needs_fixes,
            "retry_count": self.retry_count,
            "validation_issues": self.validation_issues
        }

def convert_messages_to_dict(state: Dict) -> Dict:
    """Convert state messages to a dictionary format."""
    result = {}
    for key, value in state.items():
        if isinstance(value, DeckMetadata):
            result[key] = value.to_dict()
        elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
            result[key] = value
        else:
            # Skip non-serializable objects
            continue
    return result 