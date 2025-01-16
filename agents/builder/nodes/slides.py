"""Slide generation node for the builder agent."""
from typing import List, Dict, Any
from pathlib import Path
import json
import logging
from openai import AsyncOpenAI
from ..state import BuilderState
from ...utils.content import save_content, count_slides
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

@traceable(name="process_slides")
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
        template_path = base_dir / "decks" / state["metadata"]["template"] / "slides.md"
        
        # Load template
        with open(template_path) as f:
            template = f.read()
            
        # Extract pages with tables and limitations
        summaries = state.get("page_summaries", [])
        pages_with_tables = [
            f"/img/pages/page_{s['page']}.png"
            for s in summaries
            if s.get("tableDetails", {}).get("hasTable", False)
        ]
        pages_with_limitations = [
            f"/img/pages/page_{s['page']}.png"
            for s in summaries
            if s.get("tableDetails", {}).get("hasLimitations", False)
        ]
        
        # Extract mentioned companies
        mentioned_companies = set()
        for summary in summaries:
            companies = summary.get("tableDetails", {}).get("mentionedCompanies", [])
            mentioned_companies.update(companies)
        
        logger.info(f"Found {len(pages_with_tables)} pages with tables")
        logger.info(f"Found {len(pages_with_limitations)} pages with limitations")
        logger.info(f"Found companies: {list(mentioned_companies)}")
            
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
                - When discussing a specific company's benefits or plans:
                  -- Include their logo at the start of their section using the appropriate path:
                     - FirstHealth: /img/logos/FirstHealth_logo.png
                     - US Fire: /img/logos/USFire-Premier_logo.png
                     - Ameritas: /img/logos/Ameritas_logo.png
                     - BWA: /img/logos/BWA_logo.png
                     - MBR: /img/logos/MBR_logo.png
                     - TDK: /img/logos/TDK_logo.jpg
                     - EssentialCare: /img/logos/EssentialCare_logo.png
                     - NCE: /img/logos/NCE_logo.png
                     - AFSLIC: /img/logos/AFSLIC_logo.png
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
                
                You will notice there are a lot of plans here. Create a new section for each plan.
                
                These companies are mentioned in the content, use their logos in their respective sections:
                {json.dumps(list(mentioned_companies), indent=2)}
                
                Here are the benefit pages that contain tables - use these in the benefit sections:
                {json.dumps(pages_with_tables, indent=2)}
                
                Here are the pages that contain limitations - use these in the limitations sections:
                {json.dumps(pages_with_limitations, indent=2)}
                
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
            max_tokens=8000
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
        logger.error(f"Error in process_slides: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "slide_generation"
        }
        return state 