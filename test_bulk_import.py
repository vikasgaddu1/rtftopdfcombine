"""
Test script for bulk section import functionality.
"""

import tempfile
from pathlib import Path
import pandas as pd
from src.bulk_section_import import BulkSectionImporter, import_sections_from_excel
from src.session_state import SessionState, SectionDefinition


def test_bulk_import():
    """Test bulk section import with various scenarios."""
    print("=" * 70)
    print("TEST 1: Create Sample Excel Template")
    print("=" * 70)

    importer = BulkSectionImporter()

    # Create sample template
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        template_path = Path(f.name)

    importer.create_sample_excel(template_path, include_example_data=True)
    print(f"\n[OK] Created sample template: {template_path}")

    # Read it back
    df = pd.read_excel(template_path)
    print(f"  Columns: {list(df.columns)}")
    print(f"  Rows: {len(df)}")
    print("\n  Sample data:")
    print(df.to_string(index=False))

    print("\n" + "=" * 70)
    print("TEST 2: Validate Excel File")
    print("=" * 70)

    is_valid, error_msg = importer.validate_excel_file(template_path)
    print(f"\n  Valid: {is_valid}")
    if error_msg:
        print(f"  Error: {error_msg}")
    else:
        print("  [OK] File validation passed")

    print("\n" + "=" * 70)
    print("TEST 3: Read Sections from Excel")
    print("=" * 70)

    success, sections, errors = importer.read_sections_from_excel(template_path)
    print(f"\n  Success: {success}")
    print(f"  Sections found: {len(sections)}")
    print(f"  Errors: {len(errors)}")

    print("\n  Sections:")
    for section_num, section_label in sections:
        print(f"    • {section_num}: {section_label}")

    if errors:
        print("\n  Errors:")
        for error in errors:
            print(f"    • {error}")

    print("\n" + "=" * 70)
    print("TEST 4: Import with Empty Session (No Conflicts)")
    print("=" * 70)

    session = SessionState()
    print(f"\n  Before import: {len(session.section_definitions)} sections")

    result = import_sections_from_excel(template_path, session, skip_conflicts=True)

    print(f"\n  Import result:")
    print(f"    Success: {result.success}")
    print(f"    Imported: {result.imported_count}")
    print(f"    Skipped: {result.skipped_count}")
    print(f"    Errors: {result.error_count}")
    print(f"    Conflicts: {len(result.conflicts)}")

    print(f"\n  After import: {len(session.section_definitions)} sections")
    for section in session.section_definitions[:3]:
        print(f"    • {section.section_number}: {section.section_label}")
    if len(session.section_definitions) > 3:
        print(f"    ... and {len(session.section_definitions) - 3} more")

    print("\n" + "=" * 70)
    print("TEST 5: Import Again with Conflicts")
    print("=" * 70)

    print(f"\n  Current sections: {len(session.section_definitions)}")

    result2 = import_sections_from_excel(template_path, session, skip_conflicts=True)

    print(f"\n  Import result:")
    print(f"    Success: {result2.success}")
    print(f"    Imported: {result2.imported_count}")
    print(f"    Skipped: {result2.skipped_count}")
    print(f"    Conflicts: {len(result2.conflicts)}")

    if result2.conflicts:
        print(f"\n  Conflicting entries:")
        for conflict in result2.conflicts[:3]:
            print(f"    • {conflict['section_number']}: "
                  f"Existing='{conflict['existing_label']}' vs New='{conflict['new_label']}'")

    print(f"\n  After import: {len(session.section_definitions)} sections (should be unchanged)")

    print("\n" + "=" * 70)
    print("TEST 6: Import with Missing Columns")
    print("=" * 70)

    # Create invalid Excel file
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        invalid_path = Path(f.name)

    df_invalid = pd.DataFrame({
        'section_num': ['14.1', '14.2'],  # Wrong column name
        'label': ['Test 1', 'Test 2']  # Wrong column name
    })
    df_invalid.to_excel(invalid_path, index=False)

    is_valid, error_msg = importer.validate_excel_file(invalid_path)
    print(f"\n  Valid: {is_valid}")
    print(f"  Error: {error_msg}")
    print("  [OK] Correctly detected missing columns")

    print("\n" + "=" * 70)
    print("TEST 7: Import with Empty Rows and Invalid Data")
    print("=" * 70)

    # Create Excel with mixed valid/invalid data
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        mixed_path = Path(f.name)

    df_mixed = pd.DataFrame({
        'section_number': ['16.1', None, '16.2', '', '16.3'],
        'section_label': ['Valid Section 1', 'Missing number', None, 'Empty number', 'Valid Section 3']
    })
    df_mixed.to_excel(mixed_path, index=False)

    success, sections, errors = importer.read_sections_from_excel(mixed_path)
    print(f"\n  Sections found: {len(sections)}")
    print(f"  Errors encountered: {len(errors)}")

    print("\n  Valid sections:")
    for section_num, section_label in sections:
        print(f"    • {section_num}: {section_label}")

    print("\n  Errors:")
    for error in errors:
        print(f"    • {error}")

    print("\n" + "=" * 70)
    print("TEST 8: Detect Conflicts")
    print("=" * 70)

    # Create session with existing sections
    session_with_data = SessionState()
    session_with_data.section_definitions = [
        SectionDefinition("14.1", "Existing Demographic Data"),
        SectionDefinition("14.2", "Existing Efficacy Data"),
    ]

    new_sections = [
        ("14.1", "New Demographic Data"),  # Conflict
        ("14.2", "New Efficacy Data"),     # Conflict
        ("14.3", "Safety Data"),           # No conflict
    ]

    conflicts = importer.detect_conflicts(new_sections, session_with_data.section_definitions)

    print(f"\n  Existing sections: {len(session_with_data.section_definitions)}")
    print(f"  New sections to import: {len(new_sections)}")
    print(f"  Conflicts detected: {len(conflicts)}")

    print("\n  Conflicts:")
    for conflict in conflicts:
        print(f"    • {conflict['section_number']}: "
              f"Existing='{conflict['existing_label']}' vs New='{conflict['new_label']}'")

    print("\n  [OK] Should import only: 14.3 (Safety Data)")

    # Clean up temp files
    template_path.unlink()
    invalid_path.unlink()
    mixed_path.unlink()

    print("\n" + "=" * 70)
    print("All tests completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    test_bulk_import()
