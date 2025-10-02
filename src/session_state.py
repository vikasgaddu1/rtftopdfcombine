"""
Session state management for the integrated sort feature.
Manages in-memory state for section definitions and file mappings.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime


@dataclass
class SectionDefinition:
    """Represents a single section definition."""
    section_number: str
    section_label: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "section_number": self.section_number,
            "section_label": self.section_label
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'SectionDefinition':
        """Create from dictionary."""
        return cls(
            section_number=data["section_number"],
            section_label=data["section_label"]
        )


@dataclass
class FileMapping:
    """Represents a file mapping to a section."""
    filename: str  # Without extension
    section_number: Optional[str] = None
    ignore: bool = False

    @property
    def status(self) -> str:
        """Get the status of this file mapping."""
        if self.ignore:
            return "ignored"
        elif self.section_number:
            return "mapped"
        else:
            return "unmapped"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "section_number": self.section_number,
            "ignore": self.ignore
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileMapping':
        """Create from dictionary."""
        return cls(
            filename=data["filename"],
            section_number=data.get("section_number"),
            ignore=data.get("ignore", False)
        )


@dataclass
class SessionState:
    """Manages the session state for sorting configuration."""
    sort_mode: str = "default"  # "default", "ich", "custom"
    section_definitions: List[SectionDefinition] = field(default_factory=list)
    file_mappings: List[FileMapping] = field(default_factory=list)
    rtf_files: List[Path] = field(default_factory=list)

    def clear(self):
        """Clear all session state."""
        self.sort_mode = "default"
        self.section_definitions.clear()
        self.file_mappings.clear()
        self.rtf_files.clear()

    def set_sort_mode(self, mode: str):
        """Set the sort mode and clear related data if changing."""
        if mode not in ["default", "ich", "custom"]:
            raise ValueError(f"Invalid sort mode: {mode}")

        if self.sort_mode != mode:
            self.sort_mode = mode
            # Clear section definitions when changing mode
            self.section_definitions.clear()
            # Reset file mappings but keep the files
            for mapping in self.file_mappings:
                mapping.section_number = None
                mapping.ignore = False

    def update_rtf_files(self, files: List[Path]):
        """Update the list of RTF files and sync mappings."""
        self.rtf_files = files

        # Create a set of existing filenames
        existing_filenames = {m.filename for m in self.file_mappings}

        # Add new files
        for file_path in files:
            filename = file_path.stem  # Get filename without extension
            if filename not in existing_filenames:
                self.file_mappings.append(FileMapping(filename=filename))

        # Remove mappings for files that no longer exist
        current_filenames = {f.stem for f in files}
        self.file_mappings = [
            m for m in self.file_mappings
            if m.filename in current_filenames
        ]

        # Sort mappings by filename for consistency
        self.file_mappings.sort(key=lambda m: m.filename.lower())

    def get_mapping(self, filename: str) -> Optional[FileMapping]:
        """Get the mapping for a specific filename."""
        for mapping in self.file_mappings:
            if mapping.filename == filename:
                return mapping
        return None

    def get_section(self, section_number: str) -> Optional[SectionDefinition]:
        """Get a section definition by number."""
        for section in self.section_definitions:
            if section.section_number == section_number:
                return section
        return None

    def add_section(self, section_number: str, section_label: str) -> bool:
        """Add a new section definition. Returns False if section number exists."""
        if self.get_section(section_number):
            return False
        self.section_definitions.append(
            SectionDefinition(section_number, section_label)
        )
        return True

    def update_section(self, old_number: str, new_number: str, new_label: str) -> bool:
        """Update an existing section. Returns False if new number conflicts."""
        # Check if new number conflicts with another section
        if old_number != new_number and self.get_section(new_number):
            return False

        # Update the section
        for section in self.section_definitions:
            if section.section_number == old_number:
                section.section_number = new_number
                section.section_label = new_label

                # Update all file mappings using this section
                for mapping in self.file_mappings:
                    if mapping.section_number == old_number:
                        mapping.section_number = new_number
                return True
        return False

    def delete_section(self, section_number: str) -> List[str]:
        """
        Delete a section and return list of affected files.
        Clears section assignments for affected files.
        """
        affected_files = []

        # Find and remove the section
        self.section_definitions = [
            s for s in self.section_definitions
            if s.section_number != section_number
        ]

        # Clear mappings using this section
        for mapping in self.file_mappings:
            if mapping.section_number == section_number:
                affected_files.append(mapping.filename)
                mapping.section_number = None

        return affected_files

    def validate_for_processing(self) -> tuple[bool, List[str]]:
        """
        Validate if the session state is ready for processing.
        Returns (is_valid, list_of_errors).
        """
        errors = []

        # Check if in default mode (always valid)
        if self.sort_mode == "default":
            return True, []

        # Check if we have any files to process
        non_ignored_files = [m for m in self.file_mappings if not m.ignore]
        if not non_ignored_files:
            errors.append("No files to process (all files are ignored)")

        # Check if all non-ignored files are mapped
        unmapped_files = [
            m.filename for m in non_ignored_files
            if not m.section_number
        ]
        if unmapped_files:
            errors.append(f"Unmapped files: {', '.join(unmapped_files[:5])}")
            if len(unmapped_files) > 5:
                errors.append(f"  ... and {len(unmapped_files) - 5} more")

        # Check if we have section definitions
        if not self.section_definitions and non_ignored_files:
            errors.append("No section definitions available")

        return len(errors) == 0, errors

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about the current state."""
        stats = {
            "total_files": len(self.file_mappings),
            "mapped_files": len([m for m in self.file_mappings if m.section_number and not m.ignore]),
            "unmapped_files": len([m for m in self.file_mappings if not m.section_number and not m.ignore]),
            "ignored_files": len([m for m in self.file_mappings if m.ignore]),
            "total_sections": len(self.section_definitions),
            "used_sections": len(set(m.section_number for m in self.file_mappings if m.section_number))
        }
        return stats

    def export_to_json(self, filepath: Path, project_name: str = ""):
        """Export the session state to a JSON file."""
        config = {
            "version": "1.0",
            "sort_mode": self.sort_mode,
            "created_date": datetime.now().isoformat(),
            "project_name": project_name,
            "section_definitions": [s.to_dict() for s in self.section_definitions],
            "file_mappings": [m.to_dict() for m in self.file_mappings]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def import_from_json(self, filepath: Path) -> Dict[str, Any]:
        """
        Import session state from a JSON file.
        Returns a summary of the import.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Clear current state
        self.clear()

        # Set sort mode
        self.sort_mode = config.get("sort_mode", "custom")

        # Load section definitions
        for section_data in config.get("section_definitions", []):
            self.section_definitions.append(
                SectionDefinition.from_dict(section_data)
            )

        # Load file mappings
        imported_mappings = []
        for mapping_data in config.get("file_mappings", []):
            imported_mappings.append(FileMapping.from_dict(mapping_data))

        # Match imported mappings with current files
        current_filenames = {f.stem for f in self.rtf_files}
        matched_count = 0

        for imported_mapping in imported_mappings:
            if imported_mapping.filename in current_filenames:
                # File exists, use the imported mapping
                existing_mapping = self.get_mapping(imported_mapping.filename)
                if existing_mapping:
                    existing_mapping.section_number = imported_mapping.section_number
                    existing_mapping.ignore = imported_mapping.ignore
                    matched_count += 1

        # Calculate summary
        summary = {
            "project_name": config.get("project_name", ""),
            "created_date": config.get("created_date", ""),
            "sections_loaded": len(self.section_definitions),
            "files_in_config": len(imported_mappings),
            "files_matched": matched_count,
            "files_not_in_config": len(current_filenames) - matched_count,
            "files_in_config_but_missing": len(imported_mappings) - matched_count
        }

        return summary


# Default ICH E3 sections - from iche3_categories.xlsx
# Section "14" is header-only and not assignable to files
DEFAULT_ICH_SECTIONS = [
    ("14", "Tables, Figures and Graphs Referred to But Not Included in the Text"),  # Header only
    ("14.1", "Demographic Data"),
    ("14.2", "Efficacy Data"),
    ("14.3", "Safety Data"),
    ("14.3.1", "Displays of Adverse Events"),
    ("14.3.2", "Listings of Deaths, Other Serious and Significant Adverse Events"),
    ("16.2", "Patient Data Listings"),
    ("16.2.1", "Discontinued patients"),
    ("16.2.2", "Protocol deviations"),
    ("16.2.3", "Patients excluded from the efficacy analysis"),
    ("16.2.4", "Demographic data"),
    ("16.2.5", "Compliance and/or drug concentration data (if available)"),
    ("16.2.6", "Individual efficacy response data"),
    ("16.2.7", "Adverse event listings (each patient)"),
    ("16.2.8", "Listing of individual laboratory measurements by patient"),
]

# Header-only sections (not assignable to files)
HEADER_ONLY_SECTIONS = ["14", "16.2"]


def load_default_ich_sections() -> List[SectionDefinition]:
    """
    Load the default ICH E3 sections.
    Excludes header-only sections that cannot be assigned to files.
    """
    sections = []
    for number, label in DEFAULT_ICH_SECTIONS:
        # Skip header-only sections
        if number not in HEADER_ONLY_SECTIONS:
            sections.append(SectionDefinition(number, label))
    return sections