from typing import List, Dict, Any
from pathlib import Path
import json
from openai import AsyncOpenAI

from ..state import BuilderState
from ...utils.content import save_content, count_slides

client = AsyncOpenAI()

async def process_slides(state: BuilderState) -> BuilderState:
    """Generate Slidev markdown with concise, presentation-style content"""
    try:
        summaries = state.get("page_summaries", [])
        base_dir = Path(__file__).parent.parent.parent.parent
        template_path = base_dir / "decks" / state["deck_info"]["template"] / "slides.md"
        
        # Load template
        with open(template_path) as f:
            template = f.read()
            
        messages = [
            {
                "role": "system",
                "content": """You are an expert presentation writer specializing in insurance benefits.
                
                Guidelines for slide content:
                - Use bullet points with 3-5 words each
                - Lead bullets with action verbs or key benefits
                - Highlight numbers and percentages
                - Bold key terms using **term**
                - Break complex slides into two parts (1/2, 2/2)
                - Maintain exact Slidev markdown syntax
                - Follow template structure exactly
                
                Content style:
                - Scannable: Easy to read at a glance
                - Active voice: "Covers your family" vs "Family coverage provided"
                - Numbers: Use digits (50% not fifty percent)
                - Benefits: Lead with value ("$500 daily benefit" not "Daily benefit of $500")
                - Features: Start with action ("Access 24/7 care" not "24/7 care access available")"""
            },
            {
                "role": "user",
                "content": f"""
                Use this template exactly:
                {template}
                
                Fill in the template using these summaries:
                {json.dumps(summaries, indent=2)}
                
                Follow the template's structure exactly, only replacing placeholder values wrapped in curly braces.
                Maintain all Slidev syntax, layouts, and styling.
                
                Process the summaries in sequential order to create a cohesive presentation flow.
                
                End with a thank you slide.
                """
            }
        ]
        
        # Generate content
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        
        slides_content = response.choices[0].message.content
        
        # Save to file
        output_path = Path(state["deck_info"]["path"]) / "slides.md"
        await save_content(output_path, slides_content)

        # Update state
        state["generated_slides"] = slides_content
        state["slide_count"] = count_slides(slides_content)
        
        # Add slides for audio setup
        state["slides"] = []
        for summary in summaries:
            state["slides"].append({
                "title": summary.get("title", ""),
                "content": summary.get("summary", "")
            })
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "slide_generation"
        }
        return state 