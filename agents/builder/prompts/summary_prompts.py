"""Prompts for summary generation and aggregation."""

AGGREGATE_SUMMARY_PROMPT = """You are an expert at summarizing insurance plan data into a cohesive aggregated summary for creating presentation slides and a narrative script.
Below are the instructions for the aggregated summary structure:

Cover (1 slide)
  - Display the plan name and a simple tagline summarizing the plan's purpose.

Plan Overview (1 slide)
   - Provide a high-level summary of who the plan is for (e.g., individuals, families), what it offers (e.g., healthcare, affordability), and the key benefits (e.g., accessibility, personal impact).

Core Plan Elements (2-3 slides)
   - Highlight major components like coverage areas (physician services, hospitalization, virtual visits),
     the plan structure (tiered options, co-pays, visit limits), and eligibility (individuals, families, affordability focus).

Common Service Features (2-3 slides)
   - Outline standard services such as provider networks, claims management, and support tools (e.g., dashboards, wellness programs, advocacy services).


## Plan 1

**Category 1**
- **Details with values**
- **Details with values**
**Category 2**
- **Details with values**
- **Details with values**

**Category 3**
- **Details with values**
- **Details with values**

**Category 4**
- **Details with values**
- **Details with values**

**Category 5**
- **Details with values**   
- **Details**

**Category 6**
- **Details**
    


## Plan 2

**Category 1**
- **Details with values**
- **Details with values**
- **Details with values**

**Category 2**
- **Details with values**
- **Details with values**

**Category 3**
- **Details with values**
- **Details with values**

**Category 4**
- **Details with values**

**Category 5**
- **Details with values**

**Category 6**
- **Details**


## Plan 3 (1/2)

**Category 1**
- **Details with values**
- **Details with values**
- **Details with values**
- **Details with values**

**Category 2**
- **Details with values**
- **Details with values**


## Plan 3 (2/2)

**Category 3**
- **Details with values**
- **Details with values**

**Category 4**
- **Details with values**

**Category 5**
- **Details**

**Category 6**
- **Details**

(these are the tiers for the plan)
    Plan Tiers Breakdown (8-12 slides - one slide per tier - broke higher tier plans with more benefits into multiple slides)
        - **IMPORTANT** For each plan tier, detail benefits like physician services, hospitalization details, virtual visits, prescriptions, wellness tools, and advocacy.
        - Each tier should be detailed, but the slides should be concise and to the point.


Comparison slides showing differences among the tiers.
    - Highlight the benefits of each tier, but don't be redundant.
    - should return a markdown formatted spread sheet showing key differences between tiers.

Limitations and Exclusions (1-2 slides)
   - Define exclusions (e.g., pre-existing conditions, waiting periods, prescription limitations).

Key Takeaways and Action Steps (1 slide)
   - Summarize the plan's flexibility, its balance between cost and coverage, and detail next steps for enrollment or obtaining support.

Thank You (1 slide)
   - Conclude with a branded thank you message 



Inputs:

Individual Summaries:
---------------------
{individual_summaries}

Extracted Table Information:
----------------------------
{extracted_tables}

**NEVER USE THE WORD COMPREHENSIVE**

Outline your plan for the full presentation plan. add extra detail to the plan tiers sections

return only the content without any other text or comments"""

TABLE_EXTRACTION_PROMPT = """You are an expert at analyzing presentation slides and extracting tabular data.
Focus on identifying and structuring:
1. Plan tiers and their features
2. Benefit comparisons
3. Coverage limits
4. Pricing information

Output must be a valid JSON object with this structure:
{{
    "headers": ["Column1", "Column2", ...],
    "rows": [
        ["Row1Col1", "Row1Col2", ...],
        ["Row2Col1", "Row2Col2", ...]
    ],
    "table_type": "benefits",
    "metadata": {{}}
}}

Please extract any tables from this slide."""

SETUP_SLIDES_PROMPT = """You are an expert at creating Slidev markdown presentations.
            
Guidelines for slide content:
- Follow the exact template structure provided
- Keep the content concise and impactful
- Each slide should start with a # Title
- Use --- to separate slides
- Include layout directives as specified in template
- Use v-click and v-clicks for progressive reveals
- Maintain consistent formatting throughout
- Include clear section transitions
- Do not wrap the content in ```markdown or ``` tags
- Maintain all frontmatter exactly as provided"""

SETUP_SLIDES_HUMAN_TEMPLATE = """
Use this exact template structure - maintain all formatting, frontmatter, and sections:

{template}

Generate a complete Slidev markdown presentation using this processed summary content:
{processed_summaries}

** DONT SKIP ANY SECTIONS, ESSPECIALLY THE PLAN TIERS SECTIONS **

Maintain all existing slides (intro, overview, thank you) and add the content slides in between.
Each content slide should use the appropriate layout and include v-clicks for progressive reveals."""

PROCESS_SUMMARIES_PROMPT = """You are an expert at analyzing insurance plan documents and extracting key information.

You MUST output a valid JSON object with this exact structure:
{
    "page_title": "long_and_descriptive_title_that_summarizes_the_content_of_the_slide",
    "summary": "Detailed content summary with multiple paragraphs outlining all key content",
    "tableDetails": {
        "hasBenefitsTable": true/false,  # Must be true if the page contains a benefits comparison table
        "hasLimitations": true/false  # Must be true if the page contains limitations or exclusions
    }
}

Focus on identifying and summarizing:
1. Plan features and benefits
2. Coverage details and limits
3. Cost structures and tiers
4. Special provisions and requirements

Conditions for identifying a benefits table:
- Must be a structured table format
- Must compare multiple plans or tiers
- Must list benefits or coverage details
- Examples: plan comparison tables, tier comparison tables, coverage matrices

Conditions for identifying limitations:
- Must contain explicit limitations, restrictions, or exclusions
- Examples: coverage exclusions, waiting periods, pre-existing condition clauses
- Look for terms like "limitations", "exclusions", "restrictions", "not covered", "waiting period"

**NEVER USE THE WORD COMPREHENSIVE**

Format the summary in clear, professional language suitable for presentation to stakeholders.
YOUR RESPONSE MUST BE A VALID JSON OBJECT.""" 