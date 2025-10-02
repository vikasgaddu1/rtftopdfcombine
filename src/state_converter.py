"""
Convert SessionState to DataFrame format for processing pipeline.
"""

import pandas as pd
from pathlib import Path
import logging
from typing import Optional

from src.session_state import SessionState


def session_state_to_dataframe(
    session_state: SessionState,
    titles_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Convert session state to DataFrame format expected by processing pipeline.

    Args:
        session_state: The current session state with file mappings
        titles_df: DataFrame with RTF file paths and extracted titles

    Returns:
        DataFrame with columns: filepath, title, filename_stem, section_number, section_label
    """
    # Create list to hold the final data
    final_data = []

    # Iterate through file mappings
    for mapping in session_state.file_mappings:
        # Skip ignored files
        if mapping.ignore:
            logging.info(f"Ignoring file: {mapping.filename}")
            continue

        # Find the corresponding title from titles_df
        title_row = titles_df[titles_df['filename_stem'] == mapping.filename]

        if title_row.empty:
            logging.warning(f"File '{mapping.filename}' not found in titles DataFrame")
            continue

        # Get section details
        if not mapping.section_number:
            logging.warning(f"File '{mapping.filename}' has no section number assigned")
            continue

        section = session_state.get_section(mapping.section_number)
        if not section:
            logging.error(f"Section '{mapping.section_number}' not found in definitions")
            continue

        # Build row data
        row_data = {
            'filepath': title_row.iloc[0]['filepath'],
            'title': title_row.iloc[0]['title'],
            'filename_stem': mapping.filename,
            'section_number': section.section_number,
            'section_label': section.section_label  # Generic column name for both ICH and Custom modes
        }

        final_data.append(row_data)

    # Create DataFrame
    if not final_data:
        logging.error("No valid file mappings found")
        return pd.DataFrame()

    final_df = pd.DataFrame(final_data)

    # Sort by section_number and filename_stem
    final_df = final_df.sort_values(by=['section_number', 'filename_stem'])

    logging.info(f"Created DataFrame with {len(final_df)} files for processing")
    logging.info(f"Sections included: {final_df['section_number'].unique().tolist()}")

    return final_df


def validate_session_state_for_processing(session_state: SessionState) -> tuple[bool, list[str]]:
    """
    Validate that session state is ready for processing.

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Check if we have section definitions
    if not session_state.section_definitions:
        errors.append("No section definitions available")

    # Check if we have file mappings
    if not session_state.file_mappings:
        errors.append("No files to process")
        return False, errors

    # Check if all non-ignored files are mapped
    non_ignored_files = [m for m in session_state.file_mappings if not m.ignore]

    if not non_ignored_files:
        errors.append("No files to process (all files are ignored)")
        return False, errors

    unmapped_files = [m.filename for m in non_ignored_files if not m.section_number]
    if unmapped_files:
        errors.append(f"Unmapped files ({len(unmapped_files)}): {', '.join(unmapped_files[:5])}")
        if len(unmapped_files) > 5:
            errors.append(f"  ... and {len(unmapped_files) - 5} more")

    # Check if all mapped sections exist
    for mapping in non_ignored_files:
        if mapping.section_number:
            section = session_state.get_section(mapping.section_number)
            if not section:
                errors.append(f"Section '{mapping.section_number}' referenced but not defined")

    return len(errors) == 0, errors