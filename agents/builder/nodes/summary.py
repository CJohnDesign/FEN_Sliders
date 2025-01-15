import asyncio
import json
import base64
import logging
from pathlib import Path
from ...utils import llm_utils, deck_utils
from ..state import BuilderState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logging.basicConfig(
    filename='builder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def encode_image(image_path):
    """Convert an image file to base64 encoding"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logging.error(f"Error encoding image {image_path}: {str(e)}")
        raise

async def generate_page_summaries(state: BuilderState) -> BuilderState:
    """Generate summaries for each page and save to JSON"""
    try:
        if state.get("error_context"):
            return state
            
        if not state.get("pdf_info"):
            state["error_context"] = {
                "error": "No PDF info available",
                "stage": "summary_generation"
            }
            return state
            
        # Initialize LangChain chat model for proper tracing
        model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=1024,
            temperature=0.7,
            streaming=False,
            tags=["image_analysis", "summary_generation"],
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        
        # Create ai directory if it doesn't exist
        ai_dir = Path(state["deck_info"]["path"]) / "ai"
        ai_dir.mkdir(exist_ok=True)
        
        # Get image paths
        output_dir = Path(state["pdf_info"]["output_dir"])
        image_files = sorted(output_dir.glob("slide_*.jpg"))
        
        summaries = []
        
        for img_path in image_files:
            page_num = int(img_path.stem.split('_')[1])
            logging.info(f"Processing page {page_num}")
            
            try:
                base64_image = encode_image(img_path)
            except Exception as e:
                logging.error(f"Failed to encode image for page {page_num}: {str(e)}")
                continue
                
            messages = [
                SystemMessage(content="""You are an expert presentation analyst.
                Your task is to analyze presentation content and provide:
                1. A clear, descriptive title for the content
                2. A detailed summary of the content
                3. Whether the content contains benefit information
                
                IMPORTANT: Set hasTable=true if you see ANY of:
                - Insurance plan details (100 Plan, 200A Plan, etc.)
                - Daily benefit amounts
                - Hospital confinement rates
                - Emergency room benefits
                - Surgery coverage
                - Diagnostic test coverage
                
                For example, if you see text like:
                "100 Plan provides $100/day for hospital confinement"
                You MUST set hasTable=true
                
                Return this EXACT JSON format:
                {
                    "title": "Clear descriptive title",
                    "summary": "Detailed content summary",
                    "hasTable": true
                }
                
                Or if no benefit information:
                {
                    "title": "Clear descriptive title",
                    "summary": "Detailed content summary",
                    "hasTable": false
                }"""),
                HumanMessage(content=[
                    {
                        "type": "text",
                        "text": f"This is page {page_num} of {state['pdf_info']['page_count']}. If you see ANY benefit information with amounts or rates, you MUST set hasTable=true."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ])
            ]
            
            try:
                response = await model.ainvoke(messages)
                
                # Handle response content
                try:
                    if isinstance(response.content, dict):
                        content = response.content
                    else:
                        # Clean up the response if needed
                        clean_content = response.content.strip()
                        if clean_content.startswith('```json'):
                            clean_content = clean_content[7:-3]  # Remove ```json and ```
                        content = json.loads(clean_content)
                    
                    summary_entry = {
                        "page": page_num,
                        "title": content.get("title", "Error: No Title"),
                        "summary": content.get("summary", "Error: No Summary"),
                        "hasTable": bool(content.get("hasTable", False))
                    }
                    
                    summaries.append(summary_entry)
                    logging.info(f"Page {page_num}: hasTable={content.get('hasTable', False)}")
                    
                except json.JSONDecodeError as e:
                    logging.error(f"JSON parse error on page {page_num}: {str(e)}")
                    summary_entry = {
                        "page": page_num,
                        "title": "Error: JSON Parse Error",
                        "summary": f"Failed to parse response: {str(e)}",
                        "hasTable": False
                    }
                    summaries.append(summary_entry)
                    
            except Exception as e:
                logging.error(f"Error processing page {page_num}: {str(e)}")
                summaries.append({
                    "page": page_num,
                    "title": "Error",
                    "summary": f"Failed to generate summary: {str(e)}",
                    "hasTable": False
                })
        
        # Save summaries to file
        if summaries:
            summaries_file = ai_dir / "summaries.json"
            logging.info(f"Saving {len(summaries)} summaries to {summaries_file}")
            
            try:
                with open(summaries_file, "w") as f:
                    json.dump(summaries, f, indent=2)
                logging.info("Successfully saved summaries.json")
                
                # Verify the file was saved correctly
                if summaries_file.exists():
                    with open(summaries_file) as f:
                        saved_summaries = json.load(f)
                    logging.info(f"Verified summaries.json: {len(saved_summaries)} entries")
                else:
                    logging.error("summaries.json was not created")
                    
                # Update state with summaries
                state["page_summaries"] = summaries
                
            except Exception as e:
                logging.error(f"Error saving summaries.json: {str(e)}")
                state["error_context"] = {
                    "error": f"Failed to save summaries: {str(e)}",
                    "stage": "summary_generation"
                }
                
        return state
                                    
    except Exception as e:
        state["error_context"] = {
            "error": str(e),
            "stage": "summary_generation"
        }
        return state

async def process_plan_tiers(state: BuilderState) -> BuilderState:
    """Process benefit tables into detailed plan tier summaries"""
    try:
        deck_dir = Path(state["deck_info"]["path"])
        tables_data = deck_utils.load_tables_data(deck_dir)
        
        if not tables_data["tables"]:
            return state
            
        # Initialize LangChain chat model
        model = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            streaming=False,
            tags=["plan_tier_processing"]
        )
        
        system_content = """You are an expert at analyzing insurance benefit tables and creating detailed plan summaries.
        
TASK: Create a comprehensive, cell-by-cell analysis of each insurance plan based on the CSV benefit tables.

ANALYSIS REQUIREMENTS:
1. Go through EVERY cell in the CSV data
2. For each plan (column), create two detailed sections:

First Part (1/2) - Core Hospital & Emergency Benefits:
- Hospital Admission Benefits
  * List exact admission amounts
  * Include any per-admission limits
- Daily Hospital Confinement
  * List exact daily rates
  * Include any maximum days
- ICU/CCU Benefits
  * List exact daily amounts
  * Include specialized care rates
- Emergency Room Benefits
  * List exact amounts for injury
  * List exact amounts for sickness
- Ambulance Services
  * Ground transport amounts
  * Air transport amounts

Second Part (2/2) - Additional Medical Benefits:
- Surgical Benefits
  * List exact surgical amounts
  * Include anesthesia benefits
- Outpatient Benefits
  * Office visit amounts
  * Urgent care amounts
- Diagnostic Benefits
  * X-ray amounts
  * Lab test amounts
  * Advanced imaging rates
- Specialized Benefits
  * List any unique benefits
  * Include special conditions

FORMAT:
### [Plan Name] (1/2)
Core Hospital & Emergency Benefits:
- [Category Name]
  * [Exact Benefit Amount] for [Specific Service]
  * [Additional Details/Limits]
[Continue for all core benefits]

### [Plan Name] (2/2)
Additional Medical Benefits:
- [Category Name]
  * [Exact Benefit Amount] for [Specific Service]
  * [Additional Details/Limits]
[Continue for all additional benefits]

CRITICAL REQUIREMENTS:
- Include EVERY benefit from the CSV
- Use EXACT dollar amounts
- Include ALL limits and conditions
- Group similar benefits together
- Maintain precise benefit names
- List EVERY detail from each cell
- Do not skip any information"""

        # Add table data
        for table in tables_data["tables"]:
            system_content += f"\n\nBenefit Table (Page {table['page']}):\n```csv\n{table['data']}\n```"
        
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content="""Create a comprehensive, cell-by-cell analysis of each plan's benefits. 
            Go through EVERY cell in the CSV data, maintaining exact amounts and details.
            Do not summarize or skip any information - every cell should be represented in the output.
            Group the information logically but ensure NO data is lost.""")
        ]
        
        # Generate plan tier summaries
        response = await model.ainvoke(messages)
        plan_tier_content = response.content
        
        # Save plan tier summaries
        tiers_path = Path(state["deck_info"]["path"]) / "ai" / "plan_tiers.md"
        tiers_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(tiers_path, "w") as f:
            f.write(plan_tier_content)
            
        # Add to state
        state["plan_tier_summaries"] = plan_tier_content
        
        return state
        
    except Exception as e:
        state["error_context"] = {
            "step": "plan_tier_processing",
            "error": str(e)
        }
        return state

async def process_summaries(state: BuilderState) -> BuilderState:
    """Processes summaries to generate markdown content"""
    try:
        if state.get("error_context"):
            return state
            
        if not state.get("page_summaries"):
            state["error_context"] = {
                "step": "process_summaries",
                "error": "No page summaries available"
            }
            return state
            
        # First process plan tiers
        state = await process_plan_tiers(state)
        if state.get("error_context"):
            return state
            
        if not state.get("plan_tier_summaries"):
            state["error_context"] = {
                "step": "process_summaries",
                "error": "Plan tier processing failed"
            }
            return state
            
        # Convert summaries to text
        summaries_text = json.dumps(state["page_summaries"], indent=2)
        
        # Initialize LangChain chat model for proper tracing
        model = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            streaming=False,
            tags=["summary_processing", "markdown_generation"]
        )
        
        # Create system prompt using plan tier summaries
        system_content = """You are an expert at organizing and structuring content for presentations. Your task is to generate a comprehensive markdown outline that organizes all insurance benefit information in an educational format.

IMPORTANT: The outline MUST maintain the exact plan tier information provided, including all benefit amounts and structure.

The outline must follow this EXACT structure:

## 1. Plan Tiers
[PLAN_TIERS_SECTION]

## 2. Core Plan Elements
- **Introduction & Overview**
  - Plan purpose and scope
  - Association membership (BWA, NCE, etc.)
  - Basic coverage framework
  - Key insurance concepts and terms

## 3. Common Service Features
- **Telehealth Services**
  - Availability and access
  - Covered services
- **Preventive Care & Wellness**
  - Available programs
  - Coverage details
- **Advocacy & Support**
  - Member services
  - Support resources
- **Medical Bill Management**
  - Billing assistance
  - Payment processing

## 4. Limitations & Definitions
- **Required Disclosures**
  - Coverage limitations
  - State-specific information
  - Important definitions
  - Policy terms

## 5. Key Takeaways
- Plan comparison highlights
- Value propositions
- Important reminders
- Next steps

CRITICAL REQUIREMENTS:
1. The Plan Tiers section MUST come first
2. Use the EXACT plan tier content provided
3. Do not modify or summarize the plan tier information
4. Maintain all specific benefit amounts and details
5. Keep the two-part structure for each plan"""

        # Insert the plan tier summaries exactly as they are
        plan_tiers_section = state["plan_tier_summaries"]
        system_content = system_content.replace("[PLAN_TIERS_SECTION]", plan_tiers_section)

        # Create messages array
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=f"""Create a comprehensive benefit overview that:
1. Keeps the Plan Tiers section EXACTLY as provided
2. Uses the general summaries to enhance other sections
3. Maintains all specific benefit amounts
4. Creates clear explanations of insurance concepts
5. Includes relevant policy details

The Plan Tiers section has already been processed and must be kept intact.
Focus on enhancing the other sections while preserving the plan tier information.

Here are the general summaries to incorporate:

{summaries_text}""")
        ]
        
        # Generate content
        response = await model.ainvoke(messages)
        content = response.content
        
        # Verify plan tiers section is present and in the correct position
        if "## 1. Plan Tiers" not in content or content.find("## 1. Plan Tiers") > content.find("## 2."):
            # Force correct structure if needed
            sections = content.split("##")
            reordered_content = "##" + sections[0]  # Keep any initial content
            reordered_content += "\n## 1. Plan Tiers\n" + plan_tiers_section + "\n"
            for section in sections[1:]:
                if not section.strip().startswith("1. Plan Tiers"):
                    reordered_content += "##" + section
            content = reordered_content
        
        # Save content
        script_path = Path(state["deck_info"]["path"]) / "ai" / "processed_summaries.md"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(script_path, "w") as f:
            f.write(content)
            
        # Set processed summaries in state
        state["processed_summaries"] = content
            
        return state
        
    except Exception as e:
        state["error_context"] = {
            "step": "process_summaries",
            "error": str(e)
        }
        return state 