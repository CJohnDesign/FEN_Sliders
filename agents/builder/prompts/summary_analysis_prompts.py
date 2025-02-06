"""Prompts for analyzing presentation slide summaries."""

SUMMARY_ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing presentation slides. You must output a JSON object that matches this exact structure:

{
    "page_title": "long_and_descriptive_title_that_summarizes_the_content_of_the_slide",
    "summary": "Detailed content summary with multiple paragraphs",
    "tableDetails": {
        "hasBenefitsTable": true,
        "hasLimitations": false
    },
    "page": 1
}

Analyze the slide and provide:
1. A long descriptive title that captures the main topic. this will be later saved as the filename
2. A detailed multi-paragraph summary of the content
3. Indicate if the slide contains benefit tables or limitations

Conditions of a benefit table:
- must be a table
- must cover multiple plans
- lists multiple tiers of benefits

YOUR RESPONSE MUST BE A VALID JSON OBJECT."""

SUMMARY_ANALYSIS_HUMAN_PROMPT = [
    {"type": "text", "text": "Please analyze this slide."},
    {"type": "image_url", "image_url": "{image_url}"}
]

PROCESS_SUMMARIES_PROMPT = """You are an expert at analyzing insurance plan documents and extracting key information.
Focus on identifying and summarizing:
1. Plan features and benefits
2. Coverage details and limits
3. Cost structures and tiers
4. Special provisions and requirements

For each page, provide a concise but summary that captures:
- Main topics and themes
- Key data points and figures
- Important terms and conditions
- Notable exclusions or limitations

You must output a JSON object that matches this exact structure:
{
    "title": "Descriptive title of the slide",
    "summary": "Detailed content summary with multiple paragraphs",
    "tableDetails": {
        "hasBenefitsTable": true/false,  # Must be true if the page contains a benefits comparison table
        "hasLimitations": true/false  # Must be true if the page contains limitations or exclusions
    },
    "page": 1  # Page number
}

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

Format the summary in clear, professional language suitable for presentation to stakeholders.""" 