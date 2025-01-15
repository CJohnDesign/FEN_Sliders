from pathlib import Path
from typing import List, Dict, Any
import json
from openai import AsyncOpenAI

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

async def generate_audio_script(slides: List[Dict[str, Any]], template_examples: Dict[str, Any], processed_summaries: str, deck_id: str) -> str:
    """Generate audio script from processed summaries using GPT-4o"""
    # Get the generated slides content
    base_dir = Path(__file__).parent.parent.parent
    slides_path = base_dir / "decks" / deck_id / "slides.md"
    with open(slides_path) as f:
        generated_slides = f.read()
    
    # Clean up markdown formatting from inputs
    processed_summaries = processed_summaries.replace("```markdown", "").replace("```", "").strip()
    generated_slides = generated_slides.replace("```markdown", "").replace("```", "").strip()
    template_script = template_examples.get("audio_script", "").replace("```markdown", "").replace("```", "").strip()
    
    # Create messages for the LLM
    messages = [
        {
            "role": "system",
            "content": """You are an expert at creating natural, conversational audio scripts from presentation content. 
            You excel at maintaining document structure while making the content flow naturally.
            IMPORTANT: 
            1. Only use the content provided in the processed summaries. Do not make up or add information not present in the source material.
            2. Do not include any markdown formatting, backticks, or other special characters in your response.
            3. Only use plain text with section separators in the format: ---- Section Name ----"""
        },
        {
            "role": "user",
            "content": f"""
            Based on this template example - notice the format of the headline separator, ie "---- Cover ----". maintain that perfectly:

            {template_script}
            
            Please generate a natural, conversational audio script based on these processed summaries. The script should:
            1. Use a warm, professional tone
            2. Spell out numbers (e.g., "one hundred" instead of "100")
            3. Define insurance-specific terms when first used (e.g., explaining what Fixed Indemnity means)
            4. Flow naturally between points without bullet points
            5. Keep common terms like MRI, CT, US, etc. as is
            6. Never start a paragraph with "This slide". use a natural on-topic transition instead.
            7. Follow the EXACT section structure from the processed summaries - do not deviate or add sections
            8. Maintain a clear narrative flow between sections
            9. ONLY use information present in the processed summaries
            10. Do not mention anything about "MyChoice Plans" or other content not in the source material
            
            Here are the processed summaries to use as your ONLY source of content:

            {processed_summaries}

            Here are the generated slides to match the audio script to:

            {generated_slides}

            Now in the format of the initial template, generate a natural, conversational audio script that follows the structure and content of the processed summaries EXACTLY, while matching the flow of the generated slides. Use "----" section separators as shown in the template.
            """
        }
    ]
    
    # Initialize OpenAI client
    client = AsyncOpenAI()
    
    # Get response from GPT-4
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7
    )
    
    # Extract script from response and clean up formatting
    script = response.choices[0].message.content.strip()
    script = script.replace("```markdown", "").replace("```", "").strip()
    script = script.replace("**", "").replace("*", "").replace("#", "").strip()
    script = script.replace("Audio Script", "").strip()
    
    return script.strip()

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