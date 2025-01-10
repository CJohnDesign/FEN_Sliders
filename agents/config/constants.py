from typing import Dict, Any
from pathlib import Path

# Base paths
BASE_PATH = Path('decks')
TEMPLATE_PREFIX = 'FEN_'

# Template configurations
VALID_TEMPLATES = ['US', 'MC', 'PM']

# Slide configurations
SLIDE_DELIMITERS = {
    'start': '---',
    'front_matter': '---'
}

# Error messages
ERROR_MESSAGES = {
    'template_not_found': 'Template {} not found',
    'invalid_template': 'Invalid template. Must be one of: {}',
    'slides_not_found': 'Slides file not found in {}',
    'invalid_deck_id': 'Invalid deck ID format'
}

# Validation rules
VALIDATION_RULES: Dict[str, Any] = {
    'default': {
        'min_slides': 1,
        'max_slides': 100,
        'required_sections': ['content']
    }
} 