"""Content utilities for the builder agent."""
from pathlib import Path

async def save_content(path: Path, content: str) -> None:
    """Save content to file"""
    path.write_text(content, encoding='utf-8')

def count_slides(content: str) -> int:
    """Count number of slides in markdown content"""
    return content.count('---') 