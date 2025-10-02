# Pattern-Based Section Mapping Implementation Plan

## Overview
This document outlines the implementation of a pattern-based section assignment feature that allows users to map multiple files to sections using patterns (regex or wildcards) instead of individual file-by-file assignment.

## Use Cases

### Primary Use Case
A user has 50 files with names like `fslb01a.rtf`, `fslb01b.rtf`, `fslb02a.rtf`, etc., and wants to assign all of them to section "14.3.1 - Displays of Adverse Events" without clicking on each file individually.

### Additional Use Cases
1. **Category-based assignment**: All files starting with "ae" go to section 14.3, files starting with "dm" go to section 14.2
2. **Suffix-based assignment**: All files ending with "_listing" go to section 16.2
3. **Complex patterns**: Files matching `^ts[ia].*01$` (tsi01, tsa01) go to a specific section
4. **Temporary patterns**: Quick one-time assignment using file selection + pattern

## Implementation Architecture

### 1. Core Data Structure

```python
# In src/pattern_rules.py
@dataclass
class PatternRule:
    pattern: str  # Regex or wildcard pattern
    section_number: str
    description: str = ""
    priority: int = 0  # For conflict resolution
    is_regex: bool = True
    is_active: bool = True
```

### 2. Integration Points

#### A. Session State Enhancement
```python
# In src/session_state.py
@dataclass
class SessionState:
    # ... existing fields ...
    pattern_rules: List[PatternRule] = field(default_factory=list)
    pattern_rule_manager: PatternRuleManager = field(default_factory=PatternRuleManager)
```

#### B. GUI Integration
- New "Pattern Rules" tab in Configuration
- Quick pattern button in File Mapping toolbar
- Batch operations menu

### 3. User Interface Design

#### Pattern Rules Tab Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Pattern Rules                                                │
├─────────────────────────────────────────────────────────────┤
│ [➕ Add Rule] [✏️ Edit] [🗑️ Delete] [⚡ Apply All]         │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Pattern      Section              Matches   Priority    │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ ^fslb.*      14.3.1 - Displays... 12 files  10         │ │
│ │ ^tsid.*      14.2 - Efficacy...   8 files   10         │ │
│ │ .*_ae$       14.3.2 - Listings... 5 files   5          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Pattern Details:                                            │
│ Pattern: [^fslb.*        ] [x] Regex  [ ] Wildcard         │
│ Section: [14.3.1 - Displays of Adverse Events ▼]           │
│ Priority: [10    ] (Higher = override lower priority)      │
│ Description: [Files for adverse event displays    ]        │
│                                                             │
│ Preview (12 matching files):                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ✓ fslb01a                                               │ │
│ │ ✓ fslb01b                                               │ │
│ │ ✓ fslb02a                                               │ │
│ │ ...                                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [Test Pattern] [Save Rule] [Cancel]                        │
└─────────────────────────────────────────────────────────────┘
```

#### Quick Pattern Dialog
```
┌─────────────────────────────────────────────────────────────┐
│ Quick Pattern Assignment                                     │
├─────────────────────────────────────────────────────────────┤
│ Selected Files (5):                                         │
│ • fslb01a, fslb01b, fslb02a, fslb02b, fslb03a             │
│                                                             │
│ Suggested Pattern: ^fslb.*                                 │
│                                                             │
│ Pattern: [^fslb.*        ] [x] Regex  [ ] Wildcard        │
│                                                             │
│ This pattern matches 12 total files:                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ✓ fslb01a  ✓ fslb01b  ✓ fslb02a  ✓ fslb02b           │ │
│ │ ✓ fslb03a  ✓ fslb03b  ✓ fslb04a  ✓ fslb04b           │ │
│ │ ✓ fslb05a  ✓ fslb05b  ✓ fslb06a  ✓ fslb06b           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Section: [14.3.1 - Displays of Adverse Events ▼]          │
│                                                             │
│ [ ] Save as permanent rule                                 │
│                                                             │
│ [Apply to Matched Files] [Cancel]                          │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Core Functionality
1. ✅ Create `pattern_rules.py` with core classes
2. Add pattern rules to SessionState
3. Create pattern validation and testing methods
4. Implement pattern-to-mapping application logic

### Phase 2: Basic UI Integration
1. Add "Apply Pattern Rules" button to File Mapping tab
2. Create simple pattern input dialog
3. Implement preview functionality
4. Add pattern application with confirmation

### Phase 3: Advanced Features
1. Create dedicated Pattern Rules tab
2. Implement rule priority system
3. Add pattern templates and suggestions
4. Create pattern builder from file selection
5. Import/export pattern rules with config

### Phase 4: User Experience Enhancements
1. Live pattern preview while typing
2. Conflict detection and resolution
3. Undo/redo for pattern applications
4. Pattern history and favorites
5. Batch operations toolbar

## Code Examples

### Example 1: Apply Pattern via Button Click
```python
def apply_pattern_quick(self):
    """Quick pattern assignment from File Mapping tab."""
    dialog = PatternQuickDialog(self.root, self.session_state)
    
    # Get selected files or filtered files
    selected_files = self.get_selected_or_filtered_files()
    
    # Suggest pattern based on selection
    suggested_pattern = create_pattern_from_files(selected_files)
    dialog.set_pattern(suggested_pattern)
    
    if dialog.show():
        pattern = dialog.get_pattern()
        section = dialog.get_section()
        save_rule = dialog.should_save_rule()
        
        # Apply pattern
        matches = self.session_state.pattern_rule_manager.preview_matches(
            pattern, [m.filename for m in self.session_state.file_mappings]
        )
        
        # Confirm and apply
        if messagebox.askyesno("Confirm", 
            f"Apply section {section} to {len(matches)} files?"):
            
            for mapping in self.session_state.file_mappings:
                if mapping.filename in matches:
                    mapping.section_number = section
            
            if save_rule:
                rule = PatternRule(pattern, section)
                self.session_state.pattern_rule_manager.add_rule(rule)
            
            self.refresh_file_mapping_display()
```

### Example 2: Pattern Rule Priority Resolution
```python
# User defines these rules:
rules = [
    PatternRule("^fslb.*", "14.3.1", priority=10),  # All fslb files
    PatternRule("^fslb01.*", "14.3.2", priority=20), # Override for fslb01*
    PatternRule(".*_final$", "16.2", priority=5),    # Files ending in _final
]

# File "fslb01a_final" would match:
# 1. "^fslb.*" (priority 10)
# 2. "^fslb01.*" (priority 20) <- Winner (highest priority)
# 3. ".*_final$" (priority 5)
# Result: Assigned to section 14.3.2
```

### Example 3: Integration with Existing Workflow
```python
def process_with_patterns(self):
    """Enhanced processing that applies patterns first."""
    # Step 1: Apply pattern rules to unmapped files
    if self.session_state.pattern_rule_manager.rules:
        counts = self.session_state.pattern_rule_manager.apply_rules_to_mappings(
            self.session_state.file_mappings,
            override_existing=False  # Don't override manual mappings
        )
        logging.info(f"Pattern rules applied: {counts['applied']} files mapped")
    
    # Step 2: Check for remaining unmapped files
    unmapped = [m for m in self.session_state.file_mappings 
                if not m.section_number and not m.ignore]
    
    if unmapped:
        response = messagebox.askyesno(
            "Unmapped Files",
            f"{len(unmapped)} files remain unmapped. Continue anyway?"
        )
        if not response:
            return
    
    # Step 3: Continue with normal processing
    self.start_processing()
```

## Benefits

1. **Time Savings**: Map 50+ files in seconds instead of minutes
2. **Consistency**: Ensure similar files always go to the same section
3. **Reusability**: Save pattern rules for future projects
4. **Flexibility**: Mix patterns with manual overrides
5. **Error Reduction**: Less chance of mis-clicking wrong sections
6. **Scalability**: Handle projects with hundreds of files efficiently

## Migration Path

### For Existing Users
1. Pattern rules are optional - existing workflow unchanged
2. Can gradually adopt patterns for repetitive mappings
3. Import existing mappings and convert to patterns

### Configuration File Changes
```json
{
  "version": "3.0",  // Bump version for pattern rules
  "pattern_rules": [
    {
      "pattern": "^fslb.*",
      "section_number": "14.3.1",
      "priority": 10,
      "is_regex": true,
      "description": "Adverse event files"
    }
  ],
  "file_mappings": [...],  // Existing format unchanged
  // ...
}
```

## Testing Scenarios

1. **Basic Pattern Application**
   - Create pattern `^fslb.*`
   - Apply to test files
   - Verify correct assignment

2. **Priority Conflict Resolution**
   - Create overlapping patterns with different priorities
   - Verify highest priority wins

3. **Pattern Validation**
   - Test invalid regex patterns
   - Test empty patterns
   - Test wildcard vs regex modes

4. **Performance Testing**
   - Apply patterns to 500+ files
   - Measure application time
   - Verify UI responsiveness

5. **Integration Testing**
   - Apply patterns then manual override
   - Export/import with pattern rules
   - Undo/redo pattern applications

## Conclusion

The pattern-based section mapping feature will significantly improve user efficiency when dealing with large numbers of files. The implementation is designed to be:
- **Non-intrusive**: Doesn't break existing workflows
- **Intuitive**: Leverages familiar regex/wildcard concepts
- **Powerful**: Handles complex mapping scenarios
- **Flexible**: Allows mixing automatic and manual approaches

This feature addresses a real pain point in the current workflow and will make the application more scalable for enterprise use cases with hundreds of RTF files.
