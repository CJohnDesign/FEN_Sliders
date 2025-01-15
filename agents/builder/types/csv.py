"""CSV data handling for insurance benefit tables."""
from typing import List, Dict
import csv
import re
from io import StringIO
from pydantic import BaseModel, Field, field_validator

class InsuranceTableCSV(BaseModel):
    """Structured CSV data for insurance benefits."""
    headers: List[str] = Field(description="Column headers for the table")
    data: List[Dict[str, str]] = Field(description="List of rows as dictionaries")
    
    @classmethod
    def from_string(cls, csv_string: str) -> "InsuranceTableCSV":
        """Convert CSV string to structured data using csv.DictReader."""
        # Normalize line endings
        csv_string = csv_string.replace('\r\n', '\n').replace('\r', '\n')
        
        # Handle values with commas by ensuring they're quoted
        lines = csv_string.split('\n')
        processed_lines = []
        for line in lines:
            # Quote any dollar amounts with commas (e.g., $10,000)
            line = re.sub(r'(\$\d{1,3},\d{3})', r'"\1"', line)
            processed_lines.append(line)
        
        csv_string = '\n'.join(processed_lines)
        
        f = StringIO(csv_string)
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        
        # Clean and validate the data
        data = []
        for row in reader:
            # Convert any non-string values to strings and clean up
            cleaned_row = {
                str(k).strip(): cls._clean_value(v)
                for k, v in row.items()
                if k is not None
            }
            data.append(cleaned_row)
            
        return cls(headers=headers, data=data)
    
    @staticmethod
    def _clean_value(value: str | None) -> str:
        """Clean and normalize a cell value."""
        if value is None:
            return ""
        
        # Remove any quotes and extra whitespace
        value = str(value).strip().strip('"\'')
        
        # Normalize dollar amounts (remove spaces after $)
        value = re.sub(r'\$ ', '$', value)
        
        # Normalize daily rates
        value = re.sub(r'per day', '/day', value, flags=re.IGNORECASE)
        
        return value
    
    def to_string(self) -> str:
        """Convert back to CSV string using csv.DictWriter."""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=self.headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(self.data)
        return output.getvalue().strip()

    @field_validator('data')
    @classmethod
    def validate_data_structure(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Validate each row has proper string values and correct format."""
        validated_rows = []
        for row in v:
            validated_row = {}
            for key, value in row.items():
                # Ensure key is a string
                key = str(key).strip()
                
                # Clean and validate the value
                value = cls._clean_value(value)
                
                # Validate dollar amounts
                if '$' in value:
                    if not re.match(r'^\$\d+(?:,\d{3})*(?:\.\d{2})?(?:/day)?$', value):
                        raise ValueError(f"Invalid dollar amount format: {value}")
                
                validated_row[key] = value
            validated_rows.append(validated_row)
        return validated_rows

    def validate(self) -> bool:
        """Validate table structure and content."""
        try:
            # Check required headers
            if not self.headers or "Benefit Type" not in self.headers:
                return False
            
            # Check that all rows have values for all headers
            if not all(all(str(header) in row for header in self.headers) for row in self.data):
                return False
            
            # Validate each row has at least one dollar amount
            for row in self.data:
                has_dollar = any('$' in str(value) for value in row.values())
                if not has_dollar:
                    return False
            
            return True
            
        except Exception:
            return False 