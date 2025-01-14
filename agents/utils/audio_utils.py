from pathlib import Path
from typing import List, Dict, Any
import json
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.schema.messages import HumanMessage, SystemMessage

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
            
    return examples

def generate_audio_script(slides: List[Dict[str, Any]], template_examples: Dict[str, Any]) -> str:
    """Generate audio script from slides using LLM"""
    # Create the prompt for the LLM
    prompt = f"""
    Based on this template example - notice the format of the headline separator, ie "---- Cover ----". maintain that perfectly:
    ```template
    {template_examples.get("audio_script", "")}
    ```
    
    Please generate a natural, conversational audio script for these slides. The script should:
    1. Use a warm, professional tone
    2. Spell out numbers (e.g., "one hundred" instead of "100")
    3. Define insurance-specific terms when first used (e.g., explaining what Fixed Indemnity means)
    4. Flow naturally between points without bullet points
    5. Keep common terms like MRI, CT, US, etc. as is
    6. Never start a paragraph with "This slide". use a natural on-topic transition instead.
    
    PLAN SUMMARY:
    ```json
    {json.dumps([slide.get("summary", {}) for slide in slides], indent=2)}
    ```

    SLIDE CONTENT TEMPLATE:
    ```json
    {json.dumps([slide["content"] for slide in slides], indent=2)}
    ```

    Now in the format of the initial template and the slide content template + plan summary, generate a natural, conversational audio script for each slide.
    """
    
    # Initialize LLM
    llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0.7)
    
    # Create messages
    messages = [
        SystemMessage(content="You are an expert at creating natural, conversational audio scripts from presentation slides."),
        HumanMessage(content=prompt)
    ]
    
    # Get response from LLM
    response = llm.invoke(messages)
    
    # Extract script from response
    script = response.content
    
    # Ensure script starts with "# Audio Script"
    if not script.startswith("# Audio Script"):
        script = "# Audio Script\n\n" + script
        
    return script

def generate_audio_config(slides: List[Dict[str, Any]], template_examples: Dict[str, Any]) -> Dict[str, Any]:
    """Generate audio configuration from slides"""
    # Create the prompt for the LLM
    prompt = f"""
    Based on this template example:
    ```template
    {json.dumps(template_examples.get("audio_config", {}), indent=2)}
    ```
    
    Please generate an audio configuration for these slides. The config should:
    1. Include appropriate timing for each slide section
    2. Account for longer sections needing more time
    3. Sync with any click animations in the slides
    
    SLIDE CONTENT:
    ```json
    {json.dumps([slide["content"] for slide in slides], indent=2)}
    ```

    SLIDE SUMMARIES:
    ```json
    {json.dumps([slide.get("summary", {}) for slide in slides], indent=2)}
    ```
    """
    
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

async def setup_audio(deck_id: str, template: str, slides: List[Dict[str, Any]]) -> bool:
    """Set up audio script and configuration"""
    try:
        # Get deck path
        base_dir = Path(__file__).parent.parent.parent
        deck_path = base_dir / "decks" / deck_id
        
        # Load template examples
        template_examples = load_template_examples(template)
        
        # Generate audio script
        script = generate_audio_script(slides, template_examples)
        
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