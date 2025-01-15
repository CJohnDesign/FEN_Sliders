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

        # Process all summaries with tables
        tables_processed = 0
        for i, summary in enumerate(summaries):
            if summary.get("hasTable"):
                logger.info(f"Processing table on page {summary['page']}...")
                
                # Create messages for LangChain
                messages = [
                    SystemMessage(content="""You are a table extraction expert. Your task is to analyze text and extract structured data into CSV format.
                    
                    The text contains information about insurance plan benefits and their values. Extract this into a CSV table with:
                    1. A header row with plan types (e.g., "Benefit Type", "100 Plan", "200A Plan", etc.)
                    2. Data rows with benefit names and their corresponding values
                    3. Use commas as delimiters
                    4. Escape any commas in text with quotes
                    
                    Example format:
                    Benefit Type,100 Plan,200A Plan,500 Plan,1000+ Plan
                    Hospital Admission,$100,$200,$500,$1000
                    Daily Hospital Confinement,$100/day,$200/day,$500/day,$1000/day
                    Emergency Room Visit,$150,$300,$750,$1500
                    
                    Return ONLY the CSV data, with no additional text or formatting."""),
                    HumanMessage(content=f"""Here is the text containing insurance benefit information. Extract all benefit amounts and plan types into a CSV table:

{summary['summary']}

Look for:
- Different plan types (100 Plan, 200A Plan, etc.)
- Benefit types (hospital confinement, admissions, ICU, ER visits, etc.)
- Specific dollar amounts and daily rates
- Additional benefits (accidental death, etc.)

Format everything as a proper CSV table with headers and data rows.""")
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
                    
                    if csv_content:
                        try:
                            # Parse and validate CSV
                            csv_data = InsuranceTableCSV.from_string(csv_content)
                            if csv_data.validate():
                                # Store clean CSV string directly in summaries
                                summaries[i]["csv"] = csv_data.to_string()
                                tables_processed += 1
                                logger.info(f"Added CSV content for page {summary['page']}")
                            else:
                                logger.warning(f"Invalid table structure on page {summary['page']}")
                        except Exception as e:
                            logger.error(f"Failed to parse CSV on page {summary['page']}: {str(e)}")

                except Exception as e:
                    logger.error(f"Error in table extraction: {str(e)}")
                    state["error_context"] = {
                        "error": str(e),
                        "stage": "table_extraction"
                    }

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