"""Slide generation node for the builder agent."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from openai import AsyncOpenAI
from ..state import BuilderState
from ...utils.content import save_content, count_slides
from langsmith.run_helpers import traceable

# Set up logging
logger = logging.getLogger(__name__)

client = AsyncOpenAI()

@traceable(name="process_slides")
async def process_slides(state: BuilderState) -> BuilderState:
    """Generate initial Slidev markdown with presentation content"""
    try:
        if not state.get("processed_summaries"):
            state["error_context"] = {
                "error": "No processed summaries available",
                "stage": "slide_generation"
            }
            return state
            
        base_dir = Path(__file__).parent.parent.parent.parent
        template_path = base_dir / "decks" / state["metadata"]["template"] / "slides.md"
        output_path = Path(state["deck_info"]["path"]) / "slides.md"
        
        # Load template
        with open(template_path) as f:
            template = f.read()
            
        # Extract pages with tables and limitations
        summaries = state.get("summaries", [])
        pages_with_tables = [
            f"/img/pages/page_{s['page']}.png"
            for s in summaries
            if s.get("tableDetails", {}).get("hasBenefitsTable", False)
        ]
        pages_with_limitations = [
            f"/img/pages/page_{s['page']}.png"
            for s in summaries
            if s.get("tableDetails", {}).get("hasLimitations", False)
        ]
        
        logger.info(f"Found {len(pages_with_tables)} pages with tables")
        logger.info(f"Found {len(pages_with_limitations)} pages with limitations")

        # Check if slides already exist
        existing_content = ""
        if output_path.exists():
            with open(output_path) as f:
                existing_content = f.read()
                logger.info("Found existing slides content")
        
        # Create messages for slide generation
        messages = [
            {
                "role": "system",
                "content": """You are an expert presentation writer specializing in insurance benefits.
                
                Guidelines for slide content:
                - Use bullet points with 3-5 words each
                - **compress bullets into a single line. for example, per day and max day. **
                - Lead bullets with action verbs or key benefits
                - Bold important terms using **term**
                - Maintain exact Slidev syntax for layouts and transitions
                - Keep the exact section hierarchy from the summaries
                - Create slides that match the outline structure
                - When a benefit is provided by a provider, include their logo on the slide in an <img> tag
                  -- Include their logo on the slide in an <img> tag
                    -- <img src="ADD FROM BELOW" class="h-24 mix-blend-multiply" alt="Brand Logo">
                  -- Available logo paths:
                     - FirstHealth: /img/logos/FirstHealth_logo.png
                     - US Fire: /img/logos/USFire-Premier_logo.png
                     - Ameritas: /img/logos/Ameritas_logo.png
                     - BWA: /img/logos/BWA_logo.png
                     - MBR: /img/logos/MBR_logo.png
                     - TDK: /img/logos/TDK_logo.jpg
                     - EssentialCare: /img/logos/EssentialCare_logo.png
                     - NCE: /img/logos/NCE_logo.png
                     - American Financial Security Life Insurance Company: /img/logos/AFSLIC_logo.png
                     - FirstEnroll: /img/logos/FEN_logo.svg
                  -- Always include a logo if the slide mentions it and we have a logo for it.
                  -- Wrap the logo in a <v-click> with the text that mentions the associated company.
                    -- for example: <v-click>

                                    **Additional Benefit** through Partner
                                    <div class="grid grid-cols-1 gap-4 items-center px-8 py-4">
                                      <img src="" class="h-12 mix-blend-multiply" alt="Brand Logo">
                                    </div>
                                    </v-click>
                - Create a product slide for each plan slide, with the same content but split into two parts
                -- you'll notice that each plan has a slide. Longer slides are split into two parts (1/2, 2/2). Even 3 parts for long top tier sections.
                -- make sure to create two slides for each plan slide, with the same content but split into two parts
                - Do not wrap the content in ```markdown or ``` tags"""
            },
            {
                "role": "user",
                "content": f"""
                {"Use this existing slide structure as your base - maintain all layouts and transitions:" if existing_content else "Use this template structure - notice the placement of the logo images:"}
                {existing_content if existing_content else template}
                
                Generate slides using this processed summary content:
                {state["processed_summaries"]}
                
                Here are the benefit pages that contain tables - use these in the benefit sections:
                {json.dumps(pages_with_tables, indent=2)}
                
                Here are the pages that contain limitations - use these in the limitations sections:
                {json.dumps(pages_with_limitations, indent=2)}
                
                {"Update the content while maintaining the exact same structure and formatting from the existing slides." if existing_content else "Maintain all Slidev syntax for layouts and transitions."}
                Do not wrap the content in ```markdown or ``` tags.
                """
            }
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=8000
        )
        
        # Get slide content
        slides_content = response.choices[0].message.content
        
        # Save to file
        await save_content(output_path, slides_content)
        
        # Update state
        state["generated_slides"] = slides_content
        state["slide_count"] = count_slides(slides_content)
        
        # Add slides for audio setup
        state["slides"] = []
        for summary in summaries:
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