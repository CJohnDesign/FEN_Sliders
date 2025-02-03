"""Audio utilities for the builder agent."""
from pathlib import Path
from typing import List, Dict, Any
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..config.models import get_model_config
from langsmith.run_helpers import traceable
import logging

logger = logging.getLogger(__name__)

# Initialize model with config
model_config = get_model_config()
model = ChatOpenAI(**model_config)

def load_template_examples(template: str) -> Dict[str, Any]:
    """Load template files to use as examples"""
    base_dir = Path(__file__).parent.parent.parent
    template_path = base_dir / "decks" / template
    
    examples = {}
    
    # Load template audio config
    audio_config_path = template_path / "audio" / "audio_config.json"
    if audio_config_path.exists():
        with open(audio_config_path) as f:
            examples["audio_config"] = json.load(f)
            
    # Load template audio script
    audio_script_path = template_path / "audio" / "audio_script.md"
    if audio_script_path.exists():
        with open(audio_script_path) as f:
            examples["audio_script"] = f.read()

    slides_path = template_path / "slides.md"
    if slides_path.exists():
        with open(slides_path) as f:
            examples["slides"] = f.read()
            
    return examples

async def generate_audio_script(
    slides: List[Dict[str, Any]], 
    template_examples: Dict[str, Any], 
    processed_summaries: str,
    deck_name: str
) -> str:
    """Generate audio script from processed summaries using GPT-4o"""
    # Get the generated slides content
    base_dir = Path(__file__).parent.parent.parent
    slides_path = base_dir / "decks" / deck_name / "slides.md"
    
    logger.info(f"Accessing slides at path: {slides_path}")
    
    with open(slides_path) as f:
        generated_slides = f.read()
    
    # Clean up markdown formatting from inputs
    processed_summaries = processed_summaries.replace("```markdown", "").replace("```", "").strip()
    generated_slides = generated_slides.replace("```markdown", "").replace("```", "").strip()
    template_script = template_examples.get("audio_script", "").replace("```markdown", "").replace("```", "").strip()
    
    # Create messages for the LLM
    messages = [
        SystemMessage(content="""You are an expert at creating engaging, natural voice-over scripts for insurance presentations.
            Your expertise includes:
            1. Converting technical insurance content into clear, conversational narratives
            2. Maintaining perfect synchronization with slide content
            3. Creating smooth transitions between topics
            4. Explaining complex insurance terms in simple language

            CRITICAL REQUIREMENTS:
            1. ALWAYS spell out ALL numbers (e.g., "one thousand five hundred dollars" not "$1,500")
            2. Keep insurance-specific acronyms (e.g., MRI, CT, ICU) but explain them on first use
            3. Use only information from the provided content - never add or modify details
            4. Maintain exact section structure with ---- Section Name ---- format
            5. Create natural transitions between sections without using "This slide" or similar phrases
            6. Use a warm, professional tone throughout the script"""),
        HumanMessage(content=f"""
            Using this template format for reference:

            {template_script}

            Create a natural, engaging voice-over script that follows these rules:

            FORMATTING:
            1. Use ---- Section Name ---- for all section headers
            2. Start each major section with a brief introduction
            3. End each section with a smooth transition to the next topic

            CONTENT RULES:
            1. Spell out ALL numbers (e.g., "two hundred fifty dollars per day")
            2. Define insurance terms on first use (e.g., "Fixed Indemnity, which means you receive a set payment amount")
            3. Keep medical acronyms (MRI, CT, etc.) but explain them first time
            4. Use conversational transitions between points
            5. Maintain exact section order from the slides
            6. End with a warm, encouraging closing statement

            VOICE AND TONE:
            1. Professional but approachable
            2. Clear and confident
            3. Empathetic to healthcare concerns
            4. Educational without being condescending

            Here are the processed summaries to use as your source content:

            {processed_summaries}

            Here are the slides to match the script to:

            {generated_slides}
            
            ** THIS IS VERY IMPORTANT - THE SCRIPT SHOULD SPEAK TO EACH POINT OF THE SLIDES**

            Generate a natural, conversational voice-over script that perfectly matches the slide content while following all the above rules.
            """)
    ]
    
    logger.info("[GPT Call] Sending request to generate audio script")
    response = await model.ainvoke(messages)
    logger.info("[GPT Call] Received audio script response")
    
    # Extract script from response and clean up formatting
    script = response.content.strip()
    script = script.replace("```markdown", "").replace("```", "").strip()
    script = script.replace("**", "").replace("*", "").replace("#", "").strip()
    script = script.replace("Audio Script", "").strip()
    
    return script.strip()

def generate_audio_config(slides: List[Dict[str, Any]], template_examples: Dict[str, Any]) -> Dict[str, Any]:
    """Generate audio configuration from slides"""
    # For now, return a basic config - in future, use the prompt with an LLM
    return {
        "version": "1.0",
        "slides": [
            {
                "index": i + 1,
                "type": slide.get("type", "default"),
                "clicks": []
            }
            for i, slide in enumerate(slides)
        ]
    }

async def setup_audio(deck_id: str, template: str, slides: List[Dict[str, Any]], processed_summaries: str) -> bool:
    """Set up audio script and configuration"""
    try:
        # Get deck path
        base_dir = Path(__file__).parent.parent.parent
        deck_path = base_dir / "decks" / deck_id
        
        # Load template examples
        template_examples = load_template_examples(template)
        
        # Generate audio script using processed summaries
        script = await generate_audio_script(slides, template_examples, processed_summaries, deck_id)
        
        # Write audio script
        script_path = deck_path / "audio" / "audio_script.md"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        with open(script_path, "w") as f:
            f.write(script)
            
        # Generate audio config
        config = generate_audio_config(slides, template_examples)
        
        # Write audio config
        config_path = deck_path / "audio" / "audio_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            
        return True
        
    except Exception as e:
        print(f"Error setting up audio: {str(e)}")
        return False 