from typing import TypedDict, Annotated, Optional, Dict, Literal, Any
from langgraph.graph.message import add_messages
from pydantic import BaseModel

class DeckMetadata(BaseModel):
    """Metadata for deck creation and configuration."""
    deck_id: str
    title: str
    template: str
    theme_config: dict = {}

class BuilderState(TypedDict):
    """State management for the deck building process."""
    messages: Annotated[list, add_messages]
    metadata: DeckMetadata
    slides: list[dict]
    audio_config: Optional[dict]
    error_context: Optional[dict]
    deck_info: Optional[Dict[str, str]]
    awaiting_input: Optional[Literal["pdf_upload"]]
    pdf_path: Optional[str]
    pdf_info: Optional[Dict[str, Any]]
    pdf_analysis: Optional[Dict[str, str]]
    page_summaries: Optional[Dict[int, str]]  # Maps page numbers to their summaries
    processed_summaries: Optional[str]  # Markdown formatted processed summaries 