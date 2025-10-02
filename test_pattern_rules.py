"""
Quick test script for pattern-based mapping functionality.
"""

from src.pattern_rules import PatternRule, PatternRuleManager, create_pattern_from_files
from src.session_state import SessionState, FileMapping, SectionDefinition

def test_pattern_matching():
    """Test basic pattern matching."""
    print("=" * 60)
    print("Test 1: Basic Pattern Matching")
    print("=" * 60)

    # Create sample files
    test_files = [
        "fslb01a", "fslb01b", "fslb02a", "fslb02b",
        "tsid01", "tsid02", "tsid03",
        "dmdd01", "dmdd02",
        "ae_summary", "ae_detail"
    ]

    print(f"\nTest files ({len(test_files)}):")
    for f in test_files:
        print(f"  - {f}")

    # Test regex patterns
    patterns = [
        ("^fslb.*", "Matches files starting with 'fslb'"),
        ("^tsid.*", "Matches files starting with 'tsid'"),
        (".*ae.*", "Matches files containing 'ae'"),
        (".*01.*", "Matches files containing '01'"),
    ]

    manager = PatternRuleManager()

    for pattern, description in patterns:
        print(f"\n{description}: '{pattern}'")
        matches = manager.preview_matches(pattern, test_files, is_regex=True)
        print(f"  Matched {len(matches)} files: {', '.join(matches)}")

    print("\n" + "=" * 60)
    print("Test 2: Pattern Suggestion")
    print("=" * 60)

    # Test pattern suggestion
    selected_files = ["fslb01a", "fslb01b", "fslb02a"]
    suggested = create_pattern_from_files(selected_files)
    print(f"\nSelected files: {', '.join(selected_files)}")
    print(f"Suggested pattern: {suggested}")

    if suggested:
        matches = manager.preview_matches(suggested, test_files, is_regex=True)
        print(f"Pattern matches {len(matches)} files: {', '.join(matches)}")

    print("\n" + "=" * 60)
    print("Test 3: Priority-Based Conflict Resolution")
    print("=" * 60)

    # Create rules with different priorities
    rule1 = PatternRule("^fslb.*", "14.3.1", priority=10, description="All fslb files")
    rule2 = PatternRule("^fslb01.*", "14.3.2", priority=20, description="fslb01 files only")
    rule3 = PatternRule(".*a$", "16.2", priority=5, description="Files ending with 'a'")

    manager.add_rule(rule1)
    manager.add_rule(rule2)
    manager.add_rule(rule3)

    print(f"\nDefined {len(manager.rules)} rules:")
    for rule in manager.rules:
        print(f"  - Pattern: {rule.pattern:15s} -> Section: {rule.section_number:8s} (Priority: {rule.priority})")

    # Test conflict resolution
    test_filename = "fslb01a"
    matching_rule = manager.find_matching_rule(test_filename)

    print(f"\nFile '{test_filename}' matches:")
    for rule in manager.rules:
        if rule.matches(test_filename):
            print(f"  - {rule.pattern} (priority {rule.priority}) -> Section {rule.section_number}")

    print(f"\nWinner (highest priority): {matching_rule.pattern} -> Section {matching_rule.section_number}")

    print("\n" + "=" * 60)
    print("Test 4: Apply Rules to Mappings")
    print("=" * 60)

    # Create session state with file mappings
    session = SessionState()
    session.section_definitions = [
        SectionDefinition("14.3.1", "Displays of Adverse Events"),
        SectionDefinition("14.3.2", "Listings of Deaths and SAEs"),
        SectionDefinition("16.2", "Patient Data Listings"),
    ]

    # Create file mappings
    for filename in test_files:
        session.file_mappings.append(FileMapping(filename=filename))

    # Transfer rules to session
    session.pattern_rule_manager = manager

    print(f"\nBefore applying rules:")
    print(f"  Total files: {len(session.file_mappings)}")
    print(f"  Mapped files: {len([m for m in session.file_mappings if m.section_number])}")
    print(f"  Unmapped files: {len([m for m in session.file_mappings if not m.section_number])}")

    # Apply rules
    stats = session.pattern_rule_manager.apply_rules_to_mappings(
        session.file_mappings,
        override_existing=False
    )

    print(f"\nAfter applying rules:")
    print(f"  Applied: {stats['applied']} files")
    print(f"  Skipped: {stats['skipped']} files")
    print(f"  Failed: {stats['failed']} files")

    print(f"\nFile mappings:")
    for mapping in session.file_mappings:
        status = f"Section {mapping.section_number}" if mapping.section_number else "Unmapped"
        print(f"  {mapping.filename:15s} -> {status}")

    print("\n" + "=" * 60)
    print("Test 5: Export/Import with Pattern Rules")
    print("=" * 60)

    # Export to JSON
    import tempfile
    import json
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)

    session.export_to_json(temp_file, project_name="Pattern Test")

    print(f"\nExported session to: {temp_file}")

    # Check JSON content
    with open(temp_file, 'r') as f:
        config = json.load(f)

    print(f"  Version: {config.get('version')}")
    print(f"  Pattern rules: {len(config.get('pattern_rules', []))}")
    print(f"  File mappings: {len(config.get('file_mappings', []))}")
    print(f"  Section definitions: {len(config.get('section_definitions', []))}")

    # Import to new session
    new_session = SessionState()
    # Set some dummy RTF files for the import
    from pathlib import Path
    new_session.rtf_files = [Path(f"input/{filename}.rtf") for filename in test_files]

    summary = new_session.import_from_json(temp_file)

    print(f"\nImported to new session:")
    print(f"  Sections loaded: {summary['sections_loaded']}")
    print(f"  Files matched: {summary['files_matched']}")
    print(f"  Pattern rules: {len(new_session.pattern_rule_manager.rules)}")

    # Verify rules were imported
    print(f"\nImported rules:")
    for rule in new_session.pattern_rule_manager.rules:
        print(f"  - {rule.pattern} -> {rule.section_number} (priority {rule.priority})")

    # Clean up
    temp_file.unlink()

    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    test_pattern_matching()
