# Script-to-Slide Synchronization Guide

## Overview

This document explains the critical relationship between audio scripts and slide presentations in the FEN educational video system. Maintaining proper synchronization ensures that narration aligns perfectly with visual content during video generation.

## The Synchronization Rule

**Every slide must have a corresponding section in the audio script with the exact number of paragraphs to match the slide's visual structure.**

### The Formula

```
Total Script Paragraphs = 1 (for title) + N (number of v-clicks)
```

### Structure Breakdown

1. **Paragraph 1**: Always speaks to the slide title/headline (v-click 0)
2. **Paragraph 2+**: Each subsequent paragraph speaks to one v-click in sequence

## How It Works

### Example 1: Slide with 2 v-clicks

**Slide Structure (`slides.md`):**
```markdown
## Compliance: Insurance Carrier

<v-click>

**Core Functions:**
- Adherence to regulations
- Product approval
- Claims handling

</v-click>

<v-click>

**Responsible Parties:** CCO, Compliance Department, Legal

</v-click>
```

**Required Audio Script (`audio_script.md`):**
```markdown
---- Compliance: Insurance Carrier ----

Let's start with compliance requirements for Insurance Carriers or Underwriters.

Core compliance functions include adherence to state and federal insurance regulations, product approval and filing with state Departments of Insurance, market conduct compliance, licensing and appointment of agents and agencies, anti-money laundering or A M L programs, fair claims handling practices, consumer disclosures and protections, and data privacy and cybersecurity law such as HIPAA and G L B A.

Responsible parties include the Chief Compliance Officer or C C O, Compliance Department, Legal Counsel, Actuarial and Underwriting Compliance Teams, and Senior Management.
```

**Total Required: 3 paragraphs** (1 title + 2 v-clicks)

**Key Points:**
- First paragraph addresses the slide title naturally
- Numbers should be spelled out (e.g., "three hundred" not "300")
- Most acronyms are spelled out with spaces (A M L, D O I), except HIPAA has no spaces
- Professional but conversational tone
- Sentences can flow between v-clicks when natural (see Example 4)

### Example 2: Slide with no v-clicks

**Slide Structure (`slides.md`):**
```markdown
## Introduction

Welcome to the Insurance Value Chain Hierarchy training session.
```

**Required Audio Script (`audio_script.md`):**
```markdown
---- Introduction ----

Welcome to our session on the Insurance Value Chain Hierarchy. Today we'll explore what it is and its importance in the insurance industry.
```

**Total Required: 1 paragraph** (1 title + 0 v-clicks)

### Example 3: Slide with 5 v-clicks

**Slide Structure (`slides.md`):**
```markdown
## Key Takeaways

<v-clicks>

- Point 1 about the hierarchy
- Point 2 about functions
- Point 3 about compliance
- Point 4 about licensing
- Point 5 about responsibilities

</v-clicks>
```

**Required Audio Script (`audio_script.md`):**
```markdown
---- Key Takeaways ----

Paragraph 1: Introduction to key takeaways (speaks to title).

Paragraph 2: Explanation of point 1 (v-click 1).

Paragraph 3: Explanation of point 2 (v-click 2).

Paragraph 4: Explanation of point 3 (v-click 3).

Paragraph 5: Explanation of point 4 (v-click 4).

Paragraph 6: Explanation of point 5 (v-click 5).
```

**Total Required: 6 paragraphs** (1 title + 5 v-clicks)

### Example 4: Flowing Sentences Between V-Clicks (Selective Technique)

When appropriate, sentences can naturally flow across v-click boundaries, creating a more conversational presentation style. **Use this selectively** when there's a clear opportunity for natural flow.

**Example A: List with Flowing Introduction**

```markdown
---- Advocacy and Support Services ----

Let's discuss advocacy and support services.

The plan provides Personalized healthcare advocacy, 

Claims Assistance support, 

Benefit Options exploration, 

and Resource Support for members.
```

**Structure:** The sentence "The plan provides..." flows naturally across 4 v-clicks, listing each benefit as it appears.

**Example B: Mid-Sentence Clarification**

```markdown
---- Definitions and Limitations ----

When working with your clients, it's important to note that 

pre-existing conditions have a twelve-month limitation, which applies to all plans.
```

**Structure:** The thought starts before the v-click, then the key information appears with the visual reveal.

**Example C: Building Emphasis**

```markdown
---- MedFirst Overview ----

The MedFirst Plans offer a range of healthcare options 

through The Vitamin Patch Plan Sponsor.
```

**Structure:** The introduction flows into the specific detail, creating natural emphasis when the sponsor name appears.

**When to Use This Technique:**
- ✅ Natural list introductions ("The plan provides...")
- ✅ Building to a key detail or name
- ✅ Connecting related concepts smoothly
- ❌ Don't force it - complete thoughts per paragraph is perfectly fine
- ❌ Don't use for complex or technical information that needs clear separation

## Why This Matters

### For Video Generation
The video export system synchronizes narration with slide animations. Each paragraph triggers the next v-click animation, creating a seamless viewing experience.

### For Audio Generation
The audio generation system uses paragraph breaks to determine pacing and natural pauses in the narration.

### For User Experience
Proper synchronization ensures:
- Narration matches what's appearing on screen
- Viewers can follow along naturally
- Information is presented in digestible chunks
- Professional, polished educational content

## Common Mistakes to Avoid

### ❌ Mistake 1: Using `<v-clicks>` Instead of Individual `<v-click>` Tags

**Wrong:**
```markdown
<v-clicks>

- Point 1
- Point 2
- Point 3

</v-clicks>
```

**Right:**
```markdown
<v-click>

- Point 1

</v-click>

<v-click>

- Point 2

</v-click>

<v-click>

- Point 3

</v-click>
```

**Why:** Individual `<v-click>` tags give you precise control over each reveal and make it easier to match script paragraphs to visual elements.

### ❌ Mistake 2: Combining Multiple V-Clicks into One Paragraph

**Wrong:**
```markdown
---- Compliance: MGA / MGU ----

For Managing General Agents, core functions include operating within carrier-delegated authority, maintaining compliance, and conducting audits. Responsible parties include the Compliance Department.
```

**Right:**
```markdown
---- Compliance: MGA / MGU ----

For Managing General Agents, core functions include operating within carrier-delegated authority.

Responsible parties include the Compliance Department.
```

### ❌ Mistake 3: Too Many Paragraphs for V-Clicks

**Wrong:**
```markdown
---- Licensing and Contracting ----

Licensing is legal permission from the state.

Contracting is the business agreement.

Let's review the requirements.
```

**Right:**
```markdown
---- Licensing and Contracting ----

Licensing is legal permission from the state's Department of Insurance that allows selling insurance. Contracting is the business agreement you sign with carriers that lets you sell their products and earn commissions.
```

### ❌ Mistake 4: Using the Word "Comprehensive"

**Wrong:**
```markdown
This plan offers comprehensive coverage for medical expenses.
```

**Right:**
```markdown
This plan offers extensive coverage for medical expenses.
```

**Why:** The word "comprehensive" creates confusion about the scope of coverage and may mislead the audience. Use alternatives like "extensive," "broad," "wide-ranging," or be specific about what's covered.

### ❌ Mistake 5: Missing Title Paragraph

**Wrong:**
```markdown
---- Key Takeaways ----

The hierarchy shows the flow from carriers to agents.

Each entity has distinct functions.
```

**Right:**
```markdown
---- Key Takeaways ----

Here are the key takeaways from the Insurance Value Chain Hierarchy.

The hierarchy shows the flow from carriers to agents.

Each entity has distinct functions.
```

## Using the Sync Checker

### Running the Tool

```bash
node scripts/deckSyncCounter.js DECK_ID
```

Example:
```bash
node scripts/deckSyncCounter.js FEN_IVCH
```

### Understanding the Output

The tool will report any mismatches and provide clear actions:

```
❌ Sync Mismatch in Section 12:
   Slide Title: "Compliance: Insurance Carrier"
   Current script paragraphs: 2
   Slide v-clicks: 2
   📝 ACTION: Split this section into 3 paragraphs
      • Break the existing text into 3 separate paragraphs
      • Paragraph 1: Speaks to the slide title (v-click 0)
      • Paragraphs 2-3: Each speaks to one v-click (2 total v-clicks)
```

### Success Message

When everything is synchronized:

```
┌─────────────────────────────────────────────┐
│                                             │
│  ✅ All checks passed!                      │
│                                             │
│  Audio script and slides are perfectly      │
│  synchronized for deck: FEN_IVCH            │
│                                             │
└─────────────────────────────────────────────┘
```

## Content Writing Guidelines

### Script Philosophy: Light and Essential

**The slides provide the detail; the script provides the essence.**

When writing narration:
- ✅ **Communicate the core concept** rather than reading every detail on screen
- ✅ **Be concise and conversational** - viewers can see the detailed information
- ✅ **Lightly explain** what's displayed rather than exhaustively describing it
- ✅ **Touch on key points** without repeating everything verbatim
- ❌ **Don't over-narrate** what's already visible in bullet points
- ❌ **Don't list every item** when the slide shows a detailed list

**Example - Heavy vs. Light:**

**Heavy (too detailed):**
> "Core compliance functions include adherence to state and federal insurance regulations, product approval and filing with state Departments of Insurance, market conduct compliance, licensing and appointment of agents and agencies, anti-money laundering or A M L programs, fair claims handling practices, consumer disclosures and protections, data privacy and cybersecurity law such as HIPAA and G L B A, and oversight of downstream distribution partners like I M Os and F M Os."

**Light (essence-focused):**
> "Core functions include regulatory adherence, product approvals, agent licensing, A M L programs, claims handling, and data privacy like HIPAA."

The lighter version touches on the key areas while letting the slide's bullet points provide the full detail.

### Language and Tone
- **Spell out ALL numbers**: Use "two hundred fifty dollars" not "$250"
- **Professional but conversational**: Maintain warmth while staying professional
- **Active voice**: Use clear, direct language throughout
- **Natural transitions**: Create smooth flows between sections
- **Engaging**: Balance detail with keeping the audience's attention
- **Digestible**: Keep narration light enough to follow easily while watching

### Terminology
- **Explain acronyms on first use**: "Fixed Indemnity, or F I, means..."
- **Define insurance terms**: Don't assume knowledge
- **Spell out most acronyms with spaces**: A M L, D O I, C C O
- **Exception - HIPAA has no spaces**: Always write "HIPAA" not "H I P A A"
- **Keep standard medical acronyms**: MRI, CT, ICU (but explain them on first use)

### Forbidden Content
- **NEVER use "comprehensive"**: This word confuses the audience about coverage scope
- **NO placeholder comments**: Never use "---- Insert more sections ----"
- **NO shortcuts**: Never use "..." or abbreviated content
- **NO templating**: Write every section fully and explicitly

### Slide Formatting
- **Use individual `<v-click>` tags**: Never use `<v-clicks>` blocks
- **Keep content concise**: Each point should be clear and impactful
- **Progressive reveals**: Use v-clicks to build information gradually

## Best Practices

### 1. Write Slides First
Create your slide structure with v-clicks before writing the script. This ensures you know exactly how many paragraphs you need.

### 2. Count Your V-Clicks
Before writing the script section, count the v-clicks on the slide:
- No v-clicks = 1 paragraph
- 1 v-click = 2 paragraphs
- 2 v-clicks = 3 paragraphs
- And so on...

### 3. Keep Narration Light
Let the slides do the heavy lifting. Your narration should communicate the essence of what's on screen, not repeat every detail. If the slide has a detailed list, touch on the key points rather than reading every item.

### 4. Use Clear Paragraph Breaks
In the audio script, use double line breaks to separate paragraphs. This is how the sync checker identifies distinct paragraphs.

### 5. Run Sync Check Often
Run `deckSyncCounter.js` frequently during script writing to catch issues early.

### 6. Think in "Chunks"
Each paragraph should be a complete thought that matches one visual element on the slide.

### 7. Natural Flow
Ensure smooth transitions between sections with clear verbal cues at the beginning of each section. 

### 8. Complete Content
Always write out complete content for every section. Never abbreviate or use shortcuts.

### 9. Flowing Sentences Between V-Clicks
When giving a presentation, it's perfectly normal to change the slide mid-sentence. This technique is built into our system. Use it **selectively** when there's a natural opportunity (see Example 4 above for specific use cases). Don't force it - complete thoughts per paragraph work perfectly well in most cases. 

## Workflow Recommendation

1. **Design the slides** with proper v-click structure
2. **Count v-clicks** on each slide
3. **Write script sections** with the correct number of paragraphs
4. **Run sync checker** to verify alignment
5. **Fix any mismatches** by splitting or combining paragraphs
6. **Re-run sync checker** until all checks pass
7. **Generate audio and video** with confidence

## Technical Details

### Paragraph Detection
The sync checker identifies paragraphs by:
- Splitting on double line breaks (`\n\n`)
- Filtering out empty lines
- Counting non-empty text blocks

### V-Click Detection
The sync checker counts v-clicks by:
- Finding `<v-click>` tags (counts each individually)
- Finding `<v-clicks>` blocks (counts bullet points inside)
- Checking for declarative `clicks:` in slide frontmatter

### Section Matching
Sections are matched by:
- Section headers in script: `---- Title ----`
- Slide separators: `---` markers
- Sequential order (Section 1 matches Slide 1, etc.)

## Troubleshooting

### "Total issues found: X"

**Solution:** Work through each reported mismatch one at a time. The tool tells you exactly how many paragraphs each section needs.

### "Slide Count Mismatch"

**Solution:** You have a different number of sections in your script vs. slides. Add or remove sections to match.

### Section Still Failing After Fix

**Solution:** 
- Make sure you're using double line breaks (`\n\n`) between paragraphs
- Check that there's no extra whitespace causing incorrect paragraph counts
- Verify the section title matches exactly

## Related Documentation

- [Video Export Guide](./video-export-quickstart.md)
- [Audio Generation Guide](./headless-video-export.md)
- [Deck Structure Overview](./SESSION-SUMMARY.md)

## Quick Reference

| V-Clicks | Required Paragraphs | Structure |
|----------|-------------------|-----------|
| 0 | 1 | Title only |
| 1 | 2 | Title + 1 content |
| 2 | 3 | Title + 2 content |
| 3 | 4 | Title + 3 content |
| 4 | 5 | Title + 4 content |
| 5 | 6 | Title + 5 content |

**Formula:** `Paragraphs = V-Clicks + 1`

---

*Last Updated: October 15, 2025*

