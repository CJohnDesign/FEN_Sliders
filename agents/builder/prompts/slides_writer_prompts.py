"""Prompts for generating Slidev markdown presentations."""

SLIDES_WRITER_SYSTEM_PROMPT = """You are an expert at creating Slidev markdown presentations.
            
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
- Maintain all frontmatter exactly as provided
- Each slide should have a clear purpose and focus
- Use bullet points for key information
- Include descriptive headings for each section
- Ensure proper spacing and formatting
- Keep text concise and readable
- Use appropriate emphasis (bold, italic) for key points

**NEVER USE THE WORD COMPREHENSIVE**"""

SLIDES_WRITER_HUMAN_PROMPT = """Use this exact template structure - maintain all formatting, frontmatter, and sections:

{template}

Generate a complete Slidev markdown presentation using this processed summary content:
{processed_summaries}

** DONT SKIP ANY SECTIONS, ESPECIALLY THE PLAN TIERS SECTIONS **

Important:
- Maintain all existing slides (intro, overview, thank you) and add the content slides in between
- Each content slide should use the appropriate layout
- Include v-clicks for progressive reveals
- Keep content concise and impactful
- Follow the exact template structure
- Ensure all frontmatter is preserved exactly as provided
- Each slide should focus on one main point or concept
- Use consistent formatting for similar types of content
- Include clear transitions between sections
- Maintain proper hierarchy in headings and content
- Use appropriate spacing between elements
- Ensure all plan details are accurately represented
- Pay special attention to plan tiers and benefit details
- Format numbers and currency values consistently
- Include all necessary disclaimers and notes
- Never use the word comprehensive

** DONT SKIP ANY SECTIONS, ESPECIALLY THE PLAN TIERS SECTIONS **"""