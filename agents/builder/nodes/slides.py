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
        if not state.get("processed_summaries"):
            state["error_context"] = {
                "error": "No processed summaries available",
                "stage": "slide_generation"
            }
            return state
            
        base_dir = Path(__file__).parent.parent.parent.parent
        template_path = base_dir / "decks" / state["metadata"].template / "slides.md"
        
        # Load template
        with open(template_path) as f:
            template = f.read()
            
        # Create slides from processed summaries
        messages = [
            {
                "role": "system",
                "content": """You are an expert presentation writer specializing in insurance benefits.
                Guidelines for slide content:
                - Use bullet points with 3-5 words each
                - Lead bullets with action verbs or key benefits
                - Bold important terms using **term**
                - Maintain exact Slidev syntax for layouts and transitions
                - Follow template structure exactly
                - Keep the exact section hierarchy from the template
                - Create slides that match the outline structure
                - Create a product slide for each plan slide, with the same content but split into two parts
                -- you'll notice that the plan slides are split into two parts (1/2, 2/2)
                -- make sure to create two slides for each plan slide, with the same content but split into two parts
                - Do not wrap the content in ```markdown or ``` tags
                """
            },
            {
                "role": "user",
                "content": f"""
                Use this template structure:
                {template}
                
                Create slides from this processed summary content:
                {state["processed_summaries"]}
                
                Follow the template's structure exactly, only replacing placeholder values wrapped in curly braces.
                Maintain all Slidev syntax for layouts and transitions.
                Do not wrap the content in ```markdown or ``` tags.
                End with a thank you slide in this format:

                ---
                transition: fade-out
                layout: end
                line: Thank you for participating in the Premier Insurance Offer Review. Continue to be great!
                ---

                # Thank You!

                Continue to be great!
                """
            }
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        
        final_content = response.choices[0].message.content
        
        # Save to file
        output_path = Path(state["deck_info"]["path"]) / "slides.md"
        await save_content(output_path, final_content)
        
        # Update state
        state["generated_slides"] = final_content
        state["slide_count"] = count_slides(final_content)
        
        # Add slides for audio setup
        state["slides"] = []
        for summary in state.get("page_summaries", []):
            state["slides"].append({
                "title": summary.get("title", ""),
                "content": summary.get("summary", ""),
                "type": "default"
            })
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "slide_generation"
        }
        return state 