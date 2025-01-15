from typing import TypedDict, Annotated, Optional, Dict, Literal, Any, List
from langgraph.graph.message import add_messages
from pydantic import BaseModel

class PageSummary(TypedDict):
    """Structure for individual page summaries."""
    page: int
    title: str
    summary: str
    hasTable: bool
    csv: Optional[str]

class DeckMetadata(BaseModel):
    """Metadata for deck creation and configuration."""
    deck_id: str
    title: str
    template: str
    theme_config: dict = {}

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
    
    # Error handling
    error_context: Optional[dict]  # Error information if any step fails 