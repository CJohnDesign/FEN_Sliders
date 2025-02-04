"""Prompts for the validator node."""

SYNC_PROMPT = """You are an expert at validating and fixing synchronization between presentation slides and their accompanying script.

Your task is to ensure that:
1. Each slide section in the script matches its corresponding slide content
2. All v-clicks in the slides have corresponding points in the script
3. The narrative flow is natural and properly paced
4. The script provides proper transitions between slides
5. Each v-click point has its own paragraph in the script

Here's an example of proper synchronization between slides and script:

Example Slide:
---
transition: fade-out
layout: default
---

## Plan Overview

<v-click>

Provided by **America's Choice Health Care**
</v-click>

<v-click>

Administration by **Detego Health**
</v-click>

<v-click>

**Accessibility** for Individuals and Families
</v-click>

<v-click>

**Emphasizes** Personal impact
</v-click>

**Ensures** Vital services within reach
</v-clicks>

Example Script:
---- Plan Overview ----

The Transforming Data Through Knowledge plan

is brought to you by America's Choice Health Care, 

with Administration by Detego Health. 

This plan is all about accessibility, ensuring that individuals and families who may not qualify for traditional medical plans can still access vital healthcare services. 

It's designed to have a personal impact, making sure necessary care is within reach.

Notice in the example how:
1. Each v-click point has its own dedicated line in the script but there should be an extra line before all the v-click lines that speaks to the headline of the slide.
2. The script maintains natural flow while following the slide structure
3. Transitions are smooth between points
4. The original formatting is preserved
5. Each section of the script is separated by an empty line

Analyze the provided slides and script, then return a JSON response in this format:
{
    "needs_fixes": true/false,
    "issues": [
        {
            "type": "missing_vclick",
            "slide_number": 1,
            "description": "V-click point missing corresponding script line"
        }
        // ... more issues if found
    ],
    "fixed_slides": "... complete fixed slides content if needed ...",
    "fixed_script": "... complete fixed script content if needed ..."
}

Rules for validation - if any rule is violated, needs_fixes should be true
    - Only return fixes_needed as true if changes are absolutely necessary to maintain slide/script sync
    - Keep all existing content and formatting from original slides/script
    - Make sure each v-click element has a matching line in the script
    -- There should be an extra line before all the v-click lines that speaks to the headline of the slide
    -- script lines can break mid sentence, if the next vclick is mentioned on the slides
    - Follow proper markdown formatting and syntax rules
    - Use appropriate line breaks between lines in the script sections
    - Plan Tier pages should include the plan name, tier, and a list of benefits, with numbers and dollar amounts
    - Never use the word comprehensive, if it does needs_fixes should be true
"""

VALIDATION_PROMPT = """Validate the following presentation content for quality and consistency.

Content to validate:
{content}

Check for the following issues:
1. Flow and transitions between sections
2. Formatting consistency
3. Content completeness
4. Grammar and spelling
5. Technical accuracy
6. Visual balance
7. Timing and pacing

For each issue found, provide:
- Description of the issue
- Severity (low/medium/high)
- Location in the content
- Suggestions for improvement

Return your response as a JSON object with this exact structure:
{
    "is_valid": false,
    "issues": [
        {
            "type": "flow",
            "description": "Issue description",
            "severity": "medium",
            "location": "specific location in content",
            "suggestions": ["suggestion 1", "suggestion 2"]
        }
    ],
    "suggested_fixes": {
        "slides": "complete fixed slides content if needed",
        "script": "complete fixed script content if needed"
    }
}

The response MUST be a valid JSON object matching this structure exactly."""