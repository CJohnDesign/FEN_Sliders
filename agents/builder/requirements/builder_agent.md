# Health Insurance Deck Builder - Requirements Document

## Context
The current system processes insurance plan PDFs into presentation decks using a multi-step pipeline:
1. PDF processing and image extraction
2. GPT-4V analysis of images to generate summaries

Based on this, in this sprint, we want to add a new step to the pipeline:
1. Generation of Slidev markdown presentations
2. Creation of accompanying audio scripts
3. Validate until the script and slides are in sync

The system uses LangGraph for orchestration and maintains state through a BuilderState TypedDict.

## Goals
Create a robust content generation and validation system that:
1. Generates precise Slidev markdown following templates
2. Creates natural, narrative audio scripts
3. Ensures perfect alignment between slides and script
4. Maintains insurance industry compliance and accuracy

## Core Requirements

### 1. Content Generation Architecture

#### A. Slide Generation (`gen_slides`)
```python
async def gen_slides(state: BuilderState) -> BuilderState:
    """Generate Slidev-compliant markdown from summaries"""
    requirements = {
        "format": "Slidev markdown",
        "template_compliance": True,
        "components": [
            "frontmatter",
            "slide_separators (---)",
            "v-clicks for progressive reveal",
            "image references"
        ],
        "structure": {
            "cover": "Plan introduction",
            "common_benefits": "Feature breakdown",
            "plan_specific_benefits": "Feature breakdown",
            "comparison": "Plan comparisons",
            "closing": "Key takeaways"
        }
    }
```

#### B. Script Generation (`gen_script`)
```python
async def gen_script(state: BuilderState) -> BuilderState:
    """Generate narrative audio script"""
    requirements = {
        "tone": "conversational and clear",
        "content": {
            "acronyms": "Define on first use",
            "numbers": "Spell out values",
            "timing": "Match v-click progression"
        },
        "sections": {
            "match_slides": True,
            "narrative_flow": True
        }
    }
```

### 2. Validation System

#### A. Core Validation Rules
1. **Structural Alignment**
   - Equal number of slides and script sections
   - Matching section titles
   - Proper v-click timing

2. **Content Validation**
   - All acronyms defined
   - Complete coverage of plan details
   - Accurate number representations

3. **Template Compliance**
   - Correct Slidev syntax
   - Required sections present
   - Proper image references

#### B. Validation Loop
```python
async def validate_content(state: BuilderState) -> BuilderState:
    """Orchestrate content validation and regeneration"""
    max_iterations = 3
    validation_criteria = {
        "structural": check_structural_alignment,
        "content": validate_content_accuracy,
        "template": verify_template_compliance
    }
```

### 3. Template Requirements

#### A. Slides Template
```markdown
---
theme: default
title: {plan_name}
---

# {plan_name} Overview
<v-clicks>
- Key Features
- Benefits
- Coverage Details
</v-clicks>

---
# Benefit Details
...
```

#### B. Script Template
```markdown
---- {plan_name} Overview ----
Welcome to our overview of the {plan_name} health insurance plan. 
Today we'll explore the key features and benefits that make this 
plan unique...
```

### 4. Success Criteria

#### A. Content Quality
- [ ] All slides follow Slidev syntax
- [ ] Scripts use natural, conversational language
- [ ] All technical terms explained
- [ ] Proper progression of information

#### B. Technical Requirements
- [ ] Valid Slidev markdown output
- [ ] Synchronized v-clicks and script timing
- [ ] No template syntax errors
- [ ] Proper image references

#### C. Performance Metrics
- [ ] Generation < 2 minutes per attempt
- [ ] Max 3 revision cycles
- [ ] 100% slide/script section match
- [ ] Zero undefined acronyms

### 5. Implementation Flow

1. **Initial Generation**
   ```mermaid
   graph TD
   A[Summaries] --> B[gen_slides]
   B --> C[gen_script]
   C --> D[validate_content]
   D --> E{Valid?}
   E -->|No| F[Regenerate]
   E -->|Yes| G[Complete]
   F --> B
   ```

2. **Validation Loop**
   - Check structure
   - Verify content
   - Validate template
   - Provide specific feedback
   - Trigger regeneration if needed

### 6. Error Handling

1. **Generation Errors**
   - Template parsing failures
   - Content generation timeouts
   - Invalid markdown syntax

2. **Validation Errors**
   - Section count mismatches
   - Missing required content
   - Template compliance failures

### 7. Output Examples

#### A. Valid Slide Output
```markdown
---
theme: default
title: Premium Health Plus
---

# Premium Health Plus Plan
<v-clicks>
- Comprehensive coverage starting at $250/month
- Includes dental and vision benefits
- Access to nationwide provider network
</v-clicks>
```

#### B. Valid Script Output
```markdown
---- Premium Health Plus Plan ----
Let me introduce you to our Premium Health Plus Plan. 
This comprehensive health insurance plan starts at two hundred 
and fifty dollars per month. One key feature is the inclusion 
of both dental and vision benefits...
```

Would you like me to elaborate on any of these sections or provide more specific implementation details?
