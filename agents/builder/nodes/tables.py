import os
import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..state import BuilderState
from ..types.csv import InsuranceTableCSV

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def extract_tables(state: BuilderState) -> BuilderState:
    """Extract tables from slides marked with hasTable=true"""
    try:
        # Get deck directory
        deck_dir = state.get("deck_info", {}).get("path")
        if not deck_dir:
            logger.error("No deck directory found in state")
            return state

        # Create tables directory
        tables_dir = os.path.join(deck_dir, "ai", "tables")
        os.makedirs(tables_dir, exist_ok=True)

        # Initialize tables manifest
        tables_manifest = {
            "version": "1.0",
            "tables": []
        }

        # Read summaries
        summaries_path = os.path.join(deck_dir, "ai", "summaries.json")
        if not os.path.exists(summaries_path):
            logger.error(f"Summaries file not found at {summaries_path}")
            return state

        with open(summaries_path, "r") as f:
            summaries = json.load(f)

        # Initialize LangChain chat model for proper tracing
        model = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            streaming=False,
            tags=["table_extraction", "csv_generation"]
        )

        # First pass: Validate which summaries actually contain benefit tables
        for i, summary in enumerate(summaries):
            if summary.get("hasTable"):
                # Pre-check if the summary contains actual benefit data
                contains_benefits = any(keyword in summary["summary"].lower() for keyword in [
                    "plan", "benefit", "coverage", "$", "dollar", "admission", "hospital",
                    "emergency", "surgery", "physician", "diagnostic", "premium", "amount",
                    "daily", "per day", "rate", "confinement", "intensive care"
                ])
                
                # Update hasTable flag based on content analysis
                summaries[i]["hasTable"] = contains_benefits
                
                if contains_benefits:
                    logger.info(f"Page {summary['page']} contains benefit information")
                else:
                    logger.info(f"Page {summary['page']} does not contain benefit information")

        # Process all summaries with validated tables
        tables_processed = 0
        for i, summary in enumerate(summaries):
            if summary.get("hasTable"):
                logger.info(f"Processing table on page {summary['page']}...")

                # Create messages for LangChain
                messages = [
                    SystemMessage(content="""You are a table extraction expert. Your task is to analyze text and extract structured data into CSV format.
                    
                    IMPORTANT: Only extract text that represents actual benefit amounts and plan types. 
                    DO NOT create a table if the text only contains policy terms, conditions, or non-benefit information.
                    
                    The text should contain information about insurance plan benefits and their values. Extract this into a CSV table with:
                    1. A header row with plan types (e.g., "Benefit Type", "100 Plan", "200A Plan", etc.)
                    2. Data rows with benefit names and their corresponding values
                    3. Use commas as delimiters
                    4. Escape any commas in text with quotes
                    
                    Example format:
                    Benefit Type,100 Plan,200A Plan,500 Plan,1000+ Plan
                    Hospital Admission,$100,$200,$500,$1000
                    Daily Hospital Confinement,$100/day,$200/day,$500/day,$1000/day
                    Emergency Room Visit,$150,$300,$750,$1500
                    
                    If the text does not contain actual benefit amounts and plan types, return EMPTY.
                    Return ONLY the CSV data or EMPTY, with no additional text or formatting."""),
                    HumanMessage(content=f"""Here is the text to analyze for benefit information and plan types:

{summary['summary']}

Requirements:
1. ONLY extract if the text contains actual benefit amounts and plan types
2. If the text only contains policy terms, conditions, or non-benefit information, return EMPTY
3. Include all plan types found
4. Include all benefit types with their amounts
5. Format as a proper CSV table with headers and data rows

Format everything as a proper CSV table with headers and data rows, or return EMPTY if no actual benefit data is found.""")
                ]

                try:
                    # Use LangChain's model for proper tracing
                    response = await model.ainvoke(messages)
                    csv_content = response.content.strip()
                    
                    # Remove markdown code block if present
                    if csv_content.startswith("```"):
                        csv_content = csv_content.split("\n", 1)[1]  # Remove first line
                    if csv_content.endswith("```"):
                        csv_content = csv_content.rsplit("\n", 1)[0]  # Remove last line
                    csv_content = csv_content.strip()
                    
                    # Skip if empty or no actual table data
                    if csv_content and csv_content.lower() != "empty":
                        try:
                            # Parse and validate CSV
                            csv_data = InsuranceTableCSV.from_string(csv_content)
                            if csv_data.validate():
                                # Save CSV to file
                                table_filename = f"table_{summary['page']:03d}.csv"
                                table_path = os.path.join(tables_dir, table_filename)
                                
                                with open(table_path, "w") as f:
                                    f.write(csv_data.to_string())
                                
                                # Add to manifest
                                tables_manifest["tables"].append({
                                    "page": summary["page"],
                                    "filename": table_filename,
                                    "title": summary["title"],
                                    "headers": csv_data.headers,
                                    "row_count": len(csv_data.data)
                                })
                                
                                # Update summary with reference instead of raw CSV
                                summaries[i]["table_ref"] = table_filename
                                if "csv" in summaries[i]:
                                    del summaries[i]["csv"]  # Remove raw CSV data
                                
                                tables_processed += 1
                                logger.info(f"Saved table for page {summary['page']}")
                            else:
                                logger.warning(f"Invalid table structure on page {summary['page']}")
                                summaries[i]["hasTable"] = False
                        except Exception as e:
                            logger.error(f"Failed to parse CSV on page {summary['page']}: {str(e)}")
                            summaries[i]["hasTable"] = False
                    else:
                        # No actual table data found, update the flag
                        summaries[i]["hasTable"] = False
                        logger.info(f"No benefit table data found on page {summary['page']}")

                except Exception as e:
                    logger.error(f"Error in table extraction: {str(e)}")
                    state["error_context"] = {
                        "error": str(e),
                        "stage": "table_extraction"
                    }

        # Save manifest
        manifest_path = os.path.join(tables_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(tables_manifest, f, indent=2)

        # Save updated summaries
        with open(summaries_path, "w") as f:
            json.dump(summaries, f, indent=2)

        logger.info(f"Successfully processed {tables_processed} tables")
        return state

    except Exception as e:
        logger.error(f"Error in extract_tables: {str(e)}")
        state["error_context"] = {
            "error": str(e),
            "stage": "table_extraction"
        }
        return state 