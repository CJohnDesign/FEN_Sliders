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
        if not summaries:
            state["error_context"] = {
                "error": "No page summaries available",
                "stage": "slide_generation"
            }
            return state
            
        base_dir = Path(__file__).parent.parent.parent.parent
        template_path = base_dir / "decks" / state["metadata"].template / "slides.md"
        
        # Load template
        with open(template_path) as f:
            template = f.read()
            
        # Categorize summaries based on content
        categories = {
            "cover": [],
            "benefits": [],
            "limitations": [],
            "other": []
        }
        
        for summary in summaries:
            title = summary.get("title", "").lower()
            content = summary.get("summary", "").lower()
            
            if any(word in title for word in ["overview", "introduction", "premier"]):
                categories["cover"].append(summary)
            elif any(word in title for word in ["exclusion", "limitation", "restriction"]):
                categories["limitations"].append(summary)
            elif any(word in title for word in ["benefit", "coverage", "feature"]):
                categories["benefits"].append(summary)
            else:
                categories["other"].append(summary)
        
        # Process categories in chunks to handle token limits
        slides_content = []
        
        # First chunk: Cover and template structure
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
                - Do not include any content after the final Thank You slide"""
            },
            {
                "role": "user",
                "content": f"""
                Use this template structure:
                {template}
                
                Create the cover and introduction slides using:
                {json.dumps({"cover": categories["cover"]}, indent=2)}
                
                Follow the template's structure exactly, only replacing placeholder values wrapped in curly braces.
                Maintain all Slidev syntax, layouts, and styling.
                Do not include any content after the Thank You slide.
                """
            }
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        slides_content.append(response.choices[0].message.content)
        
        # Second chunk: Benefits
        if categories["benefits"]:
            messages = [
                {
                    "role": "system",
                    "content": """Create benefit slides following these guidelines:
                    - Use bullet points with 3-5 words each
                    - Lead with value propositions
                    - Highlight numbers and percentages
                    - Bold key terms using **term**
                    - Break complex slides into parts (1/2, 2/2)
                    - Do not include any content after the final slide"""
                },
                {
                    "role": "user",
                    "content": f"""
                    Create benefit slides for these summaries:
                    {json.dumps({"benefits": categories["benefits"]}, indent=2)}
                    
                    Use the same styling and format as the template.
                    Each slide should start with '---' and have a clear title.
                    Do not include any content after the final slide.
                    """
                }
            ]
            
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            slides_content.append(response.choices[0].message.content)
        
        # Third chunk: Limitations and Other
        if categories["limitations"] or categories["other"]:
            messages = [
                {
                    "role": "system",
                    "content": """Create limitation and additional slides following these guidelines:
                    - Use clear, concise bullet points
                    - Group related limitations together
                    - Bold important terms
                    - Maintain professional tone
                    - End with a proper thank you slide
                    - Do not include any content after the thank you slide"""
                },
                {
                    "role": "user",
                    "content": f"""
                    Create slides for these sections:
                    {json.dumps({"limitations": categories["limitations"], "other": categories["other"]}, indent=2)}
                    
                    Use the same styling and format as the template.
                    Each slide should start with '---' and have a clear title.
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
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            slides_content.append(response.choices[0].message.content)
        
        # Combine all content and ensure no duplicate content
        final_content = "\n".join(slides_content)
        
        # Remove any content after the last Thank You slide
        if "# Thank You!" in final_content:
            # Split on the first occurrence of the thank you section
            parts = final_content.split("---\ntransition: fade-out\nlayout: end", 1)
            final_content = parts[0].rstrip() + """
---
transition: fade-out
layout: end
line: Thank you for participating in the Premier Insurance Offer Review. Continue to be great!
---

# Thank You!

Continue to be great!"""
            
        # Save to file
        output_path = Path(state["deck_info"]["path"]) / "slides.md"
        await save_content(output_path, final_content)
        
        # Update state
        state["generated_slides"] = final_content
        state["slide_count"] = count_slides(final_content)
        
        # Add slides for audio setup
        state["slides"] = []
        for category, summaries in categories.items():
            for summary in summaries:
                state["slides"].append({
                    "title": summary.get("title", ""),
                    "content": summary.get("summary", ""),
                    "type": category
                })
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "slide_generation"
        }
        return state 