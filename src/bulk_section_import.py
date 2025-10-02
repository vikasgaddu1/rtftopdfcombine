"""
Bulk section import from Excel files.

This module provides functionality to import section definitions from Excel files
in bulk, rather than manually typing them one by one.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ImportResult:
    """Result of a bulk section import operation."""
    success: bool
    imported_count: int
    skipped_count: int
    error_count: int
    conflicts: List[Dict[str, str]]  # List of conflicting entries
    errors: List[str]  # List of error messages
    imported_sections: List[Tuple[str, str]]  # List of (section_number, section_label)


class BulkSectionImporter:
    """Handles bulk import of section definitions from Excel files."""

    REQUIRED_COLUMNS = ['section_number', 'section_label']

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_excel_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that the Excel file has the required columns.

        Args:
            file_path: Path to the Excel file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to read the Excel file
            df = pd.read_excel(file_path)

            # Check for required columns (case-insensitive)
            df_columns_lower = [col.lower() for col in df.columns]

            missing_columns = []
            for required_col in self.REQUIRED_COLUMNS:
                if required_col.lower() not in df_columns_lower:
                    missing_columns.append(required_col)

            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}"

            # Check if file has any data rows
            if len(df) == 0:
                return False, "Excel file contains no data rows"

            return True, None

        except Exception as e:
            return False, f"Error reading Excel file: {str(e)}"

    def read_sections_from_excel(self, file_path: Path) -> Tuple[bool, List[Tuple[str, str]], List[str]]:
        """
        Read section definitions from Excel file.

        Args:
            file_path: Path to the Excel file

        Returns:
            Tuple of (success, sections_list, errors_list)
            sections_list: List of (section_number, section_label) tuples
            errors_list: List of error messages for invalid rows
        """
        try:
            df = pd.read_excel(file_path)

            # Normalize column names to lowercase for case-insensitive matching
            df.columns = df.columns.str.lower()

            sections = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    section_number = str(row['section_number']).strip()
                    section_label = str(row['section_label']).strip()

                    # Skip empty rows
                    if pd.isna(row['section_number']) or pd.isna(row['section_label']):
                        continue

                    # Skip if section_number is empty after stripping
                    if not section_number or section_number.lower() == 'nan':
                        errors.append(f"Row {idx + 2}: Empty section_number")
                        continue

                    # Skip if section_label is empty after stripping
                    if not section_label or section_label.lower() == 'nan':
                        errors.append(f"Row {idx + 2}: Empty section_label")
                        continue

                    sections.append((section_number, section_label))

                except Exception as e:
                    errors.append(f"Row {idx + 2}: {str(e)}")

            return True, sections, errors

        except Exception as e:
            self.logger.error(f"Error reading Excel file: {e}")
            return False, [], [f"Failed to read Excel file: {str(e)}"]

    def detect_conflicts(self, new_sections: List[Tuple[str, str]],
                        existing_sections: List) -> List[Dict[str, str]]:
        """
        Detect conflicts between new sections and existing sections.

        Args:
            new_sections: List of (section_number, section_label) tuples to import
            existing_sections: List of existing SectionDefinition objects

        Returns:
            List of conflict dictionaries with details
        """
        conflicts = []
        existing_numbers = {s.section_number: s.section_label for s in existing_sections}

        for section_number, section_label in new_sections:
            if section_number in existing_numbers:
                conflicts.append({
                    'section_number': section_number,
                    'new_label': section_label,
                    'existing_label': existing_numbers[section_number]
                })

        return conflicts

    def import_sections(self, file_path: Path, existing_sections: List,
                       skip_conflicts: bool = True) -> ImportResult:
        """
        Import sections from Excel file with conflict detection.

        Args:
            file_path: Path to the Excel file
            existing_sections: List of existing SectionDefinition objects
            skip_conflicts: If True, skip conflicting entries; if False, fail on conflicts

        Returns:
            ImportResult object with detailed results
        """
        result = ImportResult(
            success=False,
            imported_count=0,
            skipped_count=0,
            error_count=0,
            conflicts=[],
            errors=[],
            imported_sections=[]
        )

        # Validate file
        is_valid, error_msg = self.validate_excel_file(file_path)
        if not is_valid:
            result.errors.append(error_msg)
            return result

        # Read sections from Excel
        success, new_sections, read_errors = self.read_sections_from_excel(file_path)
        if not success:
            result.errors.extend(read_errors)
            return result

        result.errors.extend(read_errors)
        result.error_count = len(read_errors)

        if not new_sections:
            result.errors.append("No valid sections found in Excel file")
            return result

        # Detect conflicts
        conflicts = self.detect_conflicts(new_sections, existing_sections)
        result.conflicts = conflicts

        if conflicts and not skip_conflicts:
            result.errors.append(f"Found {len(conflicts)} conflicting section numbers")
            result.success = False
            return result

        # Build set of existing section numbers for quick lookup
        existing_numbers = {s.section_number for s in existing_sections}

        # Import sections (skip conflicts if requested)
        for section_number, section_label in new_sections:
            if section_number in existing_numbers:
                result.skipped_count += 1
                self.logger.info(f"Skipped conflicting section: {section_number}")
            else:
                result.imported_sections.append((section_number, section_label))
                result.imported_count += 1

        result.success = True
        return result

    def create_sample_excel(self, output_path: Path, include_example_data: bool = True):
        """
        Create a sample Excel template for section import.

        Args:
            output_path: Path where to save the template
            include_example_data: If True, include example rows
        """
        if include_example_data:
            data = {
                'section_number': ['14.1', '14.2', '14.3', '14.3.1', '14.3.2'],
                'section_label': [
                    'Demographic Data',
                    'Efficacy Data',
                    'Safety Data',
                    'Displays of Adverse Events',
                    'Listings of Deaths and SAEs'
                ]
            }
        else:
            data = {
                'section_number': [],
                'section_label': []
            }

        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
        self.logger.info(f"Created sample Excel template at: {output_path}")


def import_sections_from_excel(file_path: Path, session_state,
                               skip_conflicts: bool = True) -> ImportResult:
    """
    Convenience function to import sections into a SessionState.

    Args:
        file_path: Path to the Excel file
        session_state: SessionState object to import into
        skip_conflicts: If True, skip conflicting entries

    Returns:
        ImportResult object
    """
    importer = BulkSectionImporter()
    result = importer.import_sections(file_path, session_state.section_definitions, skip_conflicts)

    if result.success and result.imported_sections:
        # Import the sections into session state
        from src.session_state import SectionDefinition
        for section_number, section_label in result.imported_sections:
            session_state.section_definitions.append(
                SectionDefinition(section_number, section_label)
            )
        logging.info(f"Successfully imported {result.imported_count} sections")

    return result
