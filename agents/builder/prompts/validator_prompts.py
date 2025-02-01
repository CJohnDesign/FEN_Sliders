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

<v-clicks>

- Provided by **America's Choice Health Care**
- Administration by **Detego Health**
- **Accessibility** for Individuals and Families
- **Emphasizes** Personal impact
- **Ensures** Vital services within reach

</v-clicks>

Example Script:
---- Plan Overview ----

The Transforming Data Through Knowledge plan

is brought to you by America's Choice Health Care, 

with Administration by Detego Health. 

This plan is all about accessibility, ensuring that individuals and families who may not qualify for traditional medical plans can still access vital healthcare services. 

It's designed to have a personal impact, making sure necessary care is within reach.

Notice in the example how:
1. Each v-click point has its own dedicated paragraph
2. The script maintains natural flow while following the slide structure
3. Transitions are smooth between points
4. The original formatting is preserved
5. Line breaks separate each section

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

Rules:
1. Only return fixes if absolutely necessary
2. Preserve all existing content and formatting
3. Each v-click should have a dedicated paragraph in the script
4. Maintain proper markdown formatting
5. Keep the original title and structure
6. Add proper line breaks between sections
7. Ensure natural transitions between slides""" 