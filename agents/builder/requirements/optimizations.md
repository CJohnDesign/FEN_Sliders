# Sketch pad for optimizations

## Short Term:

### Current Issues:

1. **Table Extraction Issue**
- The table extraction is failing because the vision model (`gpt-4o`) doesn't support image analysis
- We need to modify the table extraction code to use a different approach or model that supports image analysis
- The tables are being detected correctly (pages 2 and 11), but the extraction is failing

2. **Slide Generation Issue**
- The slide generation is failing because it depends on the processed summaries
- The processed summaries file is not being created due to the table extraction failure
- This creates a cascade of failures in the workflow

### Required Fixes:

1. **Table Extraction (High Priority)**
```python
- Update tables.py to use a proper vision model
- Consider using Azure OCR or another OCR service for table extraction
- Add better error handling for table extraction failures
- Add fallback mechanisms when table extraction fails
```

2. **Workflow Resilience**
```python
- Modify the graph to handle partial failures better
- Allow the workflow to continue even if table extraction fails
- Add checkpoints to save intermediate results
```

### Future Tasks:

1. **Content Generation**
```python
- Implement slide content generation with proper formatting
- Add support for different slide layouts
- Implement proper handling of tables in slides
- Add support for custom themes and styling
```

2. **Audio Processing**
```python
- Complete the audio processing implementation
- Add support for timing calculations
- Implement audio script generation
- Add support for different voices/languages
```

3. **Quality Assurance**
```python
- Add validation steps for generated content
- Implement content review mechanisms
- Add support for manual overrides
- Add linting and formatting checks
```

4. **Asset Management**
```python
- Improve PDF handling and verification
- Add support for multiple PDFs
- Add support for different image formats
- Implement better asset organization
```

5. **Error Handling and Recovery**
```python
- Add error logging
- Implement recovery mechanisms
- Add support for resuming failed builds
- Add validation of intermediate results
```

6. **Performance Optimization**
```python
- Add caching for model responses
- Implement parallel processing where possible
- Optimize image processing
- Add resource usage monitoring
```

### Immediate Next Steps:

1. Fix the table extraction:
```python
- Update the model in tables.py
- Add better error handling
- Test with sample tables
```

2. Implement proper workflow resilience:
```python
- Add state checkpoints
- Implement partial success handling
- Add recovery mechanisms
```

3. Complete the basic workflow:
```python
- Ensure all nodes can run to completion
- Add basic validation
- Implement minimal viable output
```

Would you like me to start working on any of these specific areas?



## Road Map:

After reviewing the codebase, here are the issues and recommendations:

1. **State Inconsistencies**:
   - `page_summaries` is typed as `Dict[int, str]` but used as a list in code
   - Some state fields like `pdf_analysis` appear unused
   - `awaiting_input` only has one literal type "pdf_upload" but could be expanded

2. **Unused or Redundant Code**:
   - `test_graph.py` seems outdated (from Jan 10)
   - `monitoring.py` was removed but some monitoring references remain
   - Multiple CSV handling approaches between `tables.py` and `summary.py`

3. **Flow Issues**:
   - No clear error recovery path in the graph
   - Missing validation steps between nodes
   - No retry mechanism for failed API calls in some nodes

4. **Documentation Gaps**:
   - `builder_agent.md` and `deck_layout_types.md` might be out of sync
   - Missing documentation for some node functions
   - Unclear type definitions for some state properties

Here's what I recommend fixing:

1. **State Cleanup**:
```python
class BuilderState(TypedDict):
    """State management for the deck building process."""
    messages: Annotated[list, add_messages]
    metadata: DeckMetadata
    slides: list[dict]
    audio_config: Optional[dict]
    error_context: Optional[dict]
    deck_info: Optional[Dict[str, str]]
    awaiting_input: Optional[Literal["pdf_upload", "validation", "audio"]]
    pdf_path: Optional[str]
    pdf_info: Optional[Dict[str, Any]]
    page_summaries: Optional[list[dict]]  # List of page summaries
    processed_summaries: Optional[str]
```

2. **Node Standardization**:
   - All nodes should follow same error handling pattern
   - Consistent API call retry mechanism
   - Standard logging format

3. **Graph Improvements**:
   - Add validation nodes
   - Implement proper error recovery paths
   - Add retry logic for failed steps

4. **File Organization**:
   - Move types to separate file
   - Create constants file for shared values
   - Standardize node structure

5. **Remove/Update**:
   - Update or remove outdated test files
   - Clean up unused state fields
   - Consolidate duplicate functionality

Would you like me to:
1. Create a detailed cleanup plan?
2. Start with fixing any specific area?
3. Show you specific code changes for any of these improvements?

The most critical issues to address first would be:
1. State type inconsistencies
2. Standardizing error handling across nodes
3. Improving the graph flow with proper validation
