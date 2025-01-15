"""TSV data handling for insurance benefit tables."""
from typing import List, Dict, Any
import csv
import io
import re
from dataclasses import dataclass

@dataclass
class InsuranceTableTSV:
    """Structured TSV data for insurance benefit tables"""
    headers: List[str]
    data: List[Dict[str, str]]

    @classmethod
    def from_string(cls, tsv_string: str) -> "InsuranceTableTSV":
        """Convert a TSV string to structured data"""
        # Read TSV using DictReader with tab delimiter
        reader = csv.DictReader(io.StringIO(tsv_string), delimiter='\t')
        headers = reader.fieldnames if reader.fieldnames else []
        data = [row for row in reader]
        
        # Clean values
        cleaned_data = []
        for row in data:
            cleaned_row = {k: cls._clean_value(v) for k, v in row.items()}
            cleaned_data.append(cleaned_row)
            
        return cls(headers=headers, data=cleaned_data)

    def to_string(self) -> str:
        """Convert structured data back to a TSV string"""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(self.data)
        return output.getvalue()

    @staticmethod
    def _clean_value(value: str) -> str:
        """Clean a cell value"""
        if not value:
            return ""
        
        # Remove any newlines or extra whitespace
        value = re.sub(r'\s+', ' ', value).strip()
        
        # Clean up dollar amounts
        value = re.sub(r'\$\s+', '$', value)
        
        return value 