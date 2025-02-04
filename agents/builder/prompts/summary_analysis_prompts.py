"""Prompts for analyzing presentation slide summaries."""

SUMMARY_ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing presentation slides. You must output a JSON object that matches this exact structure:

{{
    "page_title": "long_and_descriptive_title_that_summarizes_the_content_of_the_slide",
    "summary": "Detailed content summary with multiple paragraphs",
    "tableDetails": {{
        "hasBenefitsTable": true,
        "hasLimitations": false
    }},
    "page": 1
}}

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