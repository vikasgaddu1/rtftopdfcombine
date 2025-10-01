# Integrated Sort Feature - Implementation Plan

## Overview

This document outlines the implementation of an integrated sorting and section mapping feature directly within the GUI application. This replaces the previous external Excel file approach with a seamless in-app experience.

---

## Core Concept

### Three Sort Modes

1. **Default Sort** - Alphabetical, automatic, no user configuration
2. **ICH Sort** - Two-tab interface with pre-populated ICH E3 sections
3. **Custom Sort** - Two-tab interface where user defines their own sections

### Key Features

- **Integrated UI**: Two-tab interface (File Mapping + Section Definition) within main window
- **No External Files**: Everything managed in-app during session
- **Config Export/Import**: Save configurations as JSON for reuse
- **Real-time Validation**: Visual feedback as user works
- **Flexible Matching**: Handle files that exist/don't exist gracefully
- **Ignore Option**: Checkbox to exclude files from processing

---

## User Experience Flow

### Flow 1: Default Sort (No Changes)
```
1. User selects input folder
2. User selects "Default Sort" (radio button)
3. User clicks "Process Files"
4. Files processed alphabetically
```

### Flow 2: ICH Sort (New)
```
1. User selects input folder → Tool scans RTF files
2. User selects "ICH Sort" (radio button)
3. Two tabs appear in main window
4. Section Definition tab: Pre-populated with ICH sections (editable)
5. File Mapping tab: Shows all RTF files with dropdown + ignore checkbox
6. User maps files using dropdowns
7. User can optionally export config for reuse
8. User clicks "Process Files"
9. Tool validates → processes
```

### Flow 3: Custom Sort (New)
```
1. User selects input folder → Tool scans RTF files
2. User selects "Custom Sort" (radio button)
3. Two tabs appear in main window
4. User goes to Section Definition tab → Adds sections (Add/Edit/Delete)
5. User goes to File Mapping tab → Maps files using dropdowns
6. User can export config for reuse
7. User clicks "Process Files"
8. Tool validates → processes
```

### Flow 4: Using Saved Config
```
1. User selects input folder
2. User selects "ICH Sort" or "Custom Sort"
3. User clicks "Import Config"
4. Browses and selects previously saved JSON config
5. Section Definition tab populates with sections
6. File Mapping tab populates with matched files
7. Unmatched files show as unmapped
8. Missing files from config are ignored
9. User adjusts as needed
10. User processes files
```

---

## GUI Design

### Main Window Layout

```
┌────────────────────────────────────────────────────────┐
│ Input Folder: [C:\data\input          ] [Browse]      │
│ Output Folder: [C:\data\output        ] [Browse]      │
│                                                         │
│ Sort Mode:                                             │
│  ○ Default Sort (Alphabetical)                        │
│  ○ ICH Sort (ICH E3 Sections)                         │
│  ● Custom Sort (Define Your Own)                      │
│                                                         │
│ ┌────────────────────────────────────────────────┐   │
│ │  [File Mapping] [Section Definition]           │   │ ← Tabs (show/hide based on mode)
│ │                                                 │   │
│ │  [Tab content area - See details below]        │   │
│ │                                                 │   │
│ │                                                 │   │
│ │                                                 │   │
│ │                                                 │   │
│ └────────────────────────────────────────────────┘   │
│                                                         │
│ [Import Config] [Export Config]                       │
│                                                         │
│ PDF Options: [...]                                     │
│ [Process Files] [Stop]                                │
│                                                         │
│ Progress: [==================>        ] 45%            │
│ Status: Processing file 12 of 25...                   │
│                                                         │
│ ┌─ Log Output ─────────────────────────────────┐     │
│ │ [Log messages here...]                        │     │
│ └───────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

### Tab Behavior

**Default Sort Selected:**
- Tabs hidden/disabled
- Clean, simple interface

**ICH Sort or Custom Sort Selected:**
- Tabs visible and enabled
- File Mapping tab shows by default
- Tabs are within main window (not separate dialog)

---

## Tab 1: File Mapping

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ File Mapping                                                 │
├────────────┬──────────────────┬─────────┬──────────────────┤
│ File Name  │ Section Number   │ Ignore  │ Status           │
├────────────┼──────────────────┼─────────┼──────────────────┤
│ tsidm01    │ [▼ 14.1]        │ [ ]     │ ✅ Mapped        │
│ tsids01    │ [▼ 14.3]        │ [ ]     │ ✅ Mapped        │
│ tsfae02    │ [▼ Select...]   │ [ ]     │ ⚠️ Not Mapped    │
│ old_test   │ [▼ Select...]   │ [✓]     │ 🚫 Ignored       │
│ lsidm01    │ [▼ 16.2]        │ [ ]     │ ✅ Mapped        │
│ ...        │ ...              │ ...     │ ...              │
└────────────┴──────────────────┴─────────┴──────────────────┘

Files: 25 | Mapped: 20 | Ignored: 3 | Unmapped: 2
```

### Features

1. **Auto-populated File Names**
   - Reads from selected input folder
   - Shows filename without extension
   - Updates when input folder changes

2. **Section Number Dropdown**
   - Populated from Section Definition tab
   - Shows: "Section_Number - Section_Label"
   - Example: "14.1 - Demographic Data"
   - Empty option: "Select..."
   - Searchable/filterable (if feasible)

3. **Ignore Checkbox**
   - When checked:
     - Row grayed out
     - Section dropdown disabled
     - File excluded from PDF
     - Status shows "🚫 Ignored"
   - Logged in output report

4. **Status Column**
   - ✅ Mapped: Has section number assigned
   - ⚠️ Not Mapped: No section number
   - 🚫 Ignored: Checkbox checked
   - Auto-updates as user works

5. **Summary Bar**
   - Shows counts of mapped/unmapped/ignored files
   - Quick validation check

6. **Interactions**
   - Double-click dropdown cell to edit
   - Click checkbox to toggle ignore
   - Keyboard navigation
   - Right-click context menu (optional)

---

## Tab 2: Section Definition

### Layout - ICH Mode

```
┌──────────────────────────────────────────────────────────────┐
│ Section Definition (ICH E3 Sections)                         │
│                                                               │
│ [Add Section] [Edit Selected] [Delete Selected] [Reset]     │
│                                                               │
├─────────────────┬───────────────────────────────────────────┤
│ Section Number  │ Section Label                             │
├─────────────────┼───────────────────────────────────────────┤
│ 14.1            │ Demographic Data                          │
│ 14.1.1          │ Demographics and Baseline Characteristics│
│ 14.2            │ Efficacy Analysis                         │
│ 14.2.1          │ Primary Efficacy Endpoint                 │
│ 14.2.2          │ Secondary Efficacy Endpoints              │
│ 14.3            │ Safety Analysis                           │
│ 14.3.1          │ Deaths, SAEs, and Other Significant AEs   │
│ 14.3.2          │ Clinical Laboratory Evaluations           │
│ 14.3.3          │ Vital Signs, Physical Findings, etc.      │
│ 14.3.4          │ Adverse Events                            │
│ 16.1            │ Protocol and Amendments                   │
│ 16.2            │ Individual Data Listings                  │
│ 16.2.1          │ Subject Listings                          │
│ 16.2.2          │ Efficacy Listings                         │
│ 16.2.3          │ Safety Listings                           │
│ ...             │ ...                                        │
└─────────────────┴───────────────────────────────────────────┘

Sections: 25 | Used: 18 | Unused: 7
```

### Layout - Custom Mode

```
┌──────────────────────────────────────────────────────────────┐
│ Section Definition (Custom Sections)                         │
│                                                               │
│ [Add Section] [Edit Selected] [Delete Selected]             │
│                                                               │
├─────────────────┬───────────────────────────────────────────┤
│ Section Number  │ Section Label                             │
├─────────────────┼───────────────────────────────────────────┤
│ [Empty - Add your sections here]                            │
│                                                               │
│                                                               │
└─────────────────┴───────────────────────────────────────────┘

Sections: 0 | Use [Add Section] button to define your sections
```

### Features

1. **CRUD Operations**
   - **Add**: Click "Add Section" → Dialog with fields → Add to table
   - **Edit**: Double-click row OR select + click "Edit Selected"
   - **Delete**: Select row(s) + click "Delete Selected" (with confirmation)
   - **Reset** (ICH only): Restore default ICH sections

2. **Validation**
   - Section numbers must be unique
   - No empty values allowed
   - Warn if deleting section that's in use
   - Show error dialogs for invalid operations

3. **Used/Unused Indicator**
   - "Used" count: Sections assigned in File Mapping
   - "Unused" count: Defined but not assigned
   - Visual indicator (optional): Bold/color used sections

4. **Add/Edit Dialog**
   ```
   ┌────────────────────────────────┐
   │ Add/Edit Section               │
   │                                │
   │ Section Number:                │
   │ [14.3.5          ]             │
   │                                │
   │ Section Label:                 │
   │ [Laboratory Data ]             │
   │                                │
   │      [OK]  [Cancel]            │
   └────────────────────────────────┘
   ```

5. **ICH Mode Specifics**
   - Pre-populated on mode selection
   - Editable (user can add/modify)
   - "Reset" button to restore defaults
   - Changes persist only in session (unless exported)

6. **Custom Mode Specifics**
   - Starts empty
   - User builds from scratch
   - Import/Export for reusability

---

## Configuration Management

### Config File Format (JSON)

```json
{
  "version": "1.0",
  "sort_mode": "ICH",
  "created_date": "2024-10-01T14:30:00",
  "project_name": "Study_ABC_CSR",
  "section_definitions": [
    {
      "section_number": "14.1",
      "section_label": "Demographic Data"
    },
    {
      "section_number": "14.3",
      "section_label": "Safety Analysis"
    },
    {
      "section_number": "16.2",
      "section_label": "Individual Data Listings"
    }
  ],
  "file_mappings": [
    {
      "filename": "tsidm01",
      "section_number": "14.1",
      "ignore": false
    },
    {
      "filename": "tsids01",
      "section_number": "14.3",
      "ignore": false
    },
    {
      "filename": "lsidm01",
      "section_number": "16.2",
      "ignore": false
    },
    {
      "filename": "old_draft",
      "section_number": null,
      "ignore": true
    }
  ]
}
```

### Export Config

**Button:** "Export Config" (enabled when ICH/Custom mode selected)

**Workflow:**
1. User clicks "Export Config"
2. File Save Dialog opens
3. Default filename: `rtf2pdf_config_YYYYMMDD_HHMMSS.json`
4. User can change filename/location
5. Config saved to selected location
6. Success message: "Configuration exported to: [path]"

**What Gets Exported:**
- Sort mode (ICH or Custom)
- All section definitions
- All file mappings (including ignore status)
- Metadata (date, version)

### Import Config

**Button:** "Import Config" (enabled when ICH/Custom mode selected)

**Workflow:**
1. User clicks "Import Config"
2. File Open Dialog opens (filter: *.json)
3. User selects config file
4. Tool reads and validates JSON
5. Populates Section Definition tab
6. Matches files in File Mapping tab
7. Shows summary:
   ```
   ┌────────────────────────────────────┐
   │ Configuration Imported             │
   │                                    │
   │ Sections loaded: 15                │
   │ Files matched: 20/25               │
   │ Files not in config: 5 (unmapped) │
   │ Files in config but missing: 3    │
   │                                    │
   │ Review File Mapping tab and       │
   │ assign sections to new files.     │
   │                                    │
   │          [OK]                      │
   └────────────────────────────────────┘
   ```

**File Matching Logic:**
- Match by filename (case-insensitive)
- Files in folder but not in config: Show as unmapped
- Files in config but not in folder: Ignore silently (log warning)
- Preserve ignore status from config

### Default ICH Config

**Location:** `configs/default_ich_config.json` (shipped with app)

**Contents:**
- Complete ICH E3 section definitions
- No file mappings (empty array)
- Used as template when ICH mode selected

**When Used:**
- User selects ICH mode for first time
- User clicks "Reset" in ICH mode
- Auto-loads section definitions (not file mappings)

---

## Data Model

### In-Memory Data Structures

```python
# Current session state
class SessionState:
    sort_mode: str  # "default", "ich", "custom"
    section_definitions: List[SectionDefinition]
    file_mappings: List[FileMapping]
    rtf_files: List[Path]  # Files from input folder
    
class SectionDefinition:
    section_number: str
    section_label: str
    
class FileMapping:
    filename: str
    section_number: Optional[str]  # None if unmapped
    ignore: bool
    status: str  # "mapped", "unmapped", "ignored"
```

### Data Flow

```
Input Folder Selected
    ↓
Scan RTF Files → rtf_files list
    ↓
Sort Mode Selected
    ↓
ICH/Custom → Load/Create section_definitions
    ↓
Build file_mappings from rtf_files (initially unmapped)
    ↓
User Edits in UI
    ↓
Update in-memory structures
    ↓
Export → Write to JSON file
    ↓
Import → Read from JSON → Update in-memory structures
    ↓
Process → Validate → Convert to existing data format
```

---

## Validation Logic

### Real-time Validation (As User Works)

**File Mapping Tab:**
- Check if all non-ignored files have section numbers
- Update status column automatically
- Update summary bar counts

**Section Definition Tab:**
- Check for duplicate section numbers
- Show error when duplicate detected
- Prevent saving invalid data

### Pre-Process Validation (Before Processing)

**Checks:**
1. At least one file mapped (not all ignored)
2. All section numbers in file mappings exist in section definitions
3. No unmapped files (unless ignored)

**If Validation Fails:**
```
┌────────────────────────────────────┐
│ ⚠️ Validation Errors               │
│                                    │
│ Cannot process files:              │
│                                    │
│ • 3 files not mapped               │
│ • Files: tsfae02, tslab01, fig05  │
│                                    │
│ Please assign section numbers or  │
│ check Ignore for these files.     │
│                                    │
│ Check log for details.            │
│                                    │
│          [OK]                      │
└────────────────────────────────────┘
```

**Detailed errors in log:**
```
[ERROR] Validation failed:
[ERROR]   - File 'tsfae02' has no section number assigned
[ERROR]   - File 'tslab01' has no section number assigned
[ERROR]   - File 'fig05' has no section number assigned
[INFO] Either assign section numbers or check Ignore checkbox
```

---

## Integration with Existing Code

### Current Code Structure

```
main.py
  ↓
Calls: load_filename_section_map()
       load_ich_categories_map()
       merge_and_validate()
  ↓
Creates: final_df (DataFrame with file info + sections)
  ↓
Processes PDFs
```

### New Code Structure

```
GUI (new UI components)
  ↓
User configures in Session State
  ↓
Convert to DataFrame format
  ↓
Pass to existing processing pipeline (unchanged)
```

### Conversion Function

```python
def session_state_to_dataframe(session_state: SessionState) -> pd.DataFrame:
    """
    Convert in-memory session state to DataFrame format
    expected by existing processing code.
    
    Returns DataFrame with columns:
    - filename_stem
    - section_number
    - section_label
    - filepath
    - title (from RTF parsing - keep existing logic)
    """
    pass
```

### Modified main.py

```python
def main(config: GUIConfig, session_state: SessionState = None):
    # ... existing code ...
    
    if config.sort_mode == "default":
        # Existing automatic sorting logic
        final_df = create_automatic_sections(titles_df)
    
    elif config.sort_mode in ("ich", "custom"):
        # NEW: Convert session state to DataFrame
        if session_state is None:
            raise ValueError("Session state required for ICH/Custom mode")
        
        # Build final_df from session state
        final_df = build_final_dataframe_from_session(
            titles_df, session_state
        )
    
    # ... rest of processing unchanged ...
```

---

## Implementation Phases

### Phase 1: Foundation & UI Shell (4-6 hours)

**Tasks:**
1. Add three radio buttons to GUI (Default, ICH, Custom)
2. Create tab widget (ttk.Notebook) in main window
3. Show/hide tabs based on sort mode selection
4. Wire up basic event handlers
5. Test tab visibility toggle

**Deliverable:** UI shell with mode selection and tab visibility

**Files Modified:**
- `src/gui.py`
- `src/gui_config.py` (add sort_mode field)

---

### Phase 2: Section Definition Tab (6-8 hours)

**Tasks:**
1. Create Section Definition table widget (ttk.Treeview)
2. Implement Add Section dialog
3. Implement Edit Section (double-click)
4. Implement Delete Section (with confirmation)
5. Add validation (unique section numbers)
6. Create default ICH config JSON file
7. Load ICH sections when ICH mode selected
8. Implement Reset button (ICH mode)
9. Update summary bar (section counts)

**Deliverable:** Fully functional Section Definition tab

**Files Created:**
- `configs/default_ich_config.json`

**Files Modified:**
- `src/gui.py`
- New file: `src/section_management.py` (section CRUD logic)

---

### Phase 3: File Mapping Tab (6-8 hours)

**Tasks:**
1. Create File Mapping table widget (ttk.Treeview)
2. Auto-populate file names from input folder
3. Create dropdown (Combobox) for section selection
4. Populate dropdown from Section Definition tab
5. Implement Ignore checkbox
6. Implement Status column (auto-update)
7. Gray out ignored rows
8. Update summary bar (file counts)
9. Handle input folder change (refresh file list)

**Deliverable:** Fully functional File Mapping tab with dropdowns

**Files Modified:**
- `src/gui.py`
- New file: `src/file_mapping.py` (file mapping logic)

---

### Phase 4: Data Synchronization (3-4 hours)

**Tasks:**
1. Create SessionState data model
2. Keep Section Definition and File Mapping in sync
3. When section added/edited → Update dropdown options
4. When section deleted → Validate not in use, clear mappings if needed
5. Handle all edge cases

**Deliverable:** Tabs stay synchronized

**Files Modified:**
- `src/gui.py`
- New file: `src/session_state.py` (data model)

---

### Phase 5: Config Export/Import (4-6 hours)

**Tasks:**
1. Implement Export Config button
2. Create file save dialog with default filename
3. Serialize session state to JSON
4. Implement Import Config button
5. Create file open dialog (*.json filter)
6. Deserialize JSON to session state
7. Match files and populate tabs
8. Show import summary dialog
9. Handle errors (invalid JSON, missing fields)

**Deliverable:** Working export/import functionality

**Files Modified:**
- `src/gui.py`
- `src/session_state.py` (add export/import methods)

---

### Phase 6: Validation & Error Handling (4-5 hours)

**Tasks:**
1. Implement real-time validation in tabs
2. Implement pre-process validation
3. Create validation error dialogs
4. Add detailed logging for validation issues
5. Prevent processing if validation fails
6. Show helpful error messages

**Deliverable:** Robust validation system

**Files Modified:**
- `src/gui.py`
- `src/session_state.py` (add validation methods)

---

### Phase 7: Integration with Processing Pipeline (4-6 hours)

**Tasks:**
1. Create conversion function: SessionState → DataFrame
2. Modify main.py to accept session state
3. Build final_df from session state for ICH/Custom modes
4. Keep existing logic for Default mode
5. Handle ignored files (exclude from processing)
6. Log ignored files in output report
7. Test end-to-end processing

**Deliverable:** Full integration with existing processing

**Files Modified:**
- `main.py`
- `src/data_processing.py` (add conversion functions)

---

### Phase 8: Polish & Testing (4-6 hours)

**Tasks:**
1. Improve visual styling (colors, fonts)
2. Add keyboard shortcuts
3. Add tooltips and help text
4. Improve status messages
5. Test all user flows
6. Test edge cases
7. Fix bugs
8. Optimize performance

**Deliverable:** Production-ready feature

**Files Modified:**
- All GUI files (polish)

---

### Phase 9: Documentation (2-3 hours)

**Tasks:**
1. Update USER_GUIDE.md with new workflows
2. Document ICH sections in guide
3. Document config file format
4. Create screenshots/examples
5. Update CLI documentation (if needed)

**Deliverable:** Updated documentation

**Files Modified:**
- `docs/USER_GUIDE.md`

---

## Summary of Implementation

### Total Estimated Time: 37-49 hours (~1 week for experienced developer)

**Breakdown:**
- Phase 1: 4-6 hours (UI shell)
- Phase 2: 6-8 hours (Section Definition)
- Phase 3: 6-8 hours (File Mapping)
- Phase 4: 3-4 hours (Synchronization)
- Phase 5: 4-6 hours (Config Import/Export)
- Phase 6: 4-5 hours (Validation)
- Phase 7: 4-6 hours (Integration)
- Phase 8: 4-6 hours (Polish)
- Phase 9: 2-3 hours (Documentation)

### New Files Created
- `configs/default_ich_config.json`
- `src/session_state.py`
- `src/section_management.py`
- `src/file_mapping.py`

### Files Modified
- `src/gui.py` (major changes)
- `src/gui_config.py`
- `main.py`
- `src/data_processing.py`
- `docs/USER_GUIDE.md`

### Files No Longer Needed
- `docs/filename_section.xlsx` (deprecated)
- `docs/iche3_categories.xlsx` (replaced by JSON)

---

## Technical Considerations

### GUI Framework (tkinter)

**Widgets Needed:**
- `ttk.Notebook` for tabs
- `ttk.Treeview` for tables
- `ttk.Combobox` for dropdowns in table (custom implementation)
- `tk.Checkbutton` for ignore checkboxes
- Standard dialogs for Add/Edit

**Challenges:**
- ttk.Treeview not designed for inline editing
- Need custom solution for editable cells with dropdowns
- Consider using button that opens dropdown vs inline editing

**Approach for Dropdowns:**
- On double-click cell → Show Combobox overlay
- User selects value → Update cell → Hide Combobox
- Standard pattern for editable Treeview

### State Management

**Session State:**
- Exists only during app runtime
- Lost when app closes (unless exported)
- Refreshes when input folder changes
- Updates in real-time as user edits

**Persistence:**
- No auto-save
- User explicitly exports to JSON
- User explicitly imports from JSON
- Clean separation of in-memory vs saved state

### Performance

**Considerations:**
- Large file lists (100+ RTF files)
- Dropdown population
- Table rendering
- Real-time validation

**Optimizations:**
- Lazy loading for tables
- Debounce validation checks
- Efficient data structures
- Minimal re-renders

---

## Edge Cases & Error Handling

### Edge Case 1: Empty Input Folder
**Scenario:** User selects ICH/Custom but folder has no RTF files
**Behavior:** Show warning, disable File Mapping tab, can still define sections

### Edge Case 2: Section in Use
**Scenario:** User tries to delete section that's assigned to files
**Behavior:** Show warning with file list, ask confirmation, clear mappings if confirmed

### Edge Case 3: Invalid Config File
**Scenario:** User imports corrupted or incompatible JSON
**Behavior:** Show error dialog, don't load, log details

### Edge Case 4: Input Folder Changes
**Scenario:** User changes input folder after mapping files
**Behavior:** Ask "Refresh file list? Current mappings will be cleared." → User chooses

### Edge Case 5: Duplicate Section Number
**Scenario:** User adds section with existing number
**Behavior:** Show error immediately, don't add, suggest correction

### Edge Case 6: All Files Ignored
**Scenario:** User checks Ignore for all files
**Behavior:** Pre-process validation fails, show error

### Edge Case 7: Config Has More Files
**Scenario:** Config has 30 files, folder has 20
**Behavior:** Load 20 that match, ignore 10 missing, log info

### Edge Case 8: Config Has Fewer Files
**Scenario:** Config has 20 files, folder has 30
**Behavior:** Load 20 with mappings, show 10 as unmapped

---

## Testing Plan

### Unit Tests
- Section CRUD operations
- File mapping logic
- Validation functions
- JSON export/import
- SessionState data model

### Integration Tests
- Tab synchronization
- Config import → populate tabs
- UI → SessionState → DataFrame conversion
- End-to-end processing with session state

### Manual Testing Scenarios

**Scenario 1: ICH Happy Path**
1. Select input folder with 10 RTF files
2. Select ICH Sort
3. Verify ICH sections loaded
4. Map all files using dropdowns
5. Export config
6. Process files
7. Verify PDF generated correctly

**Scenario 2: Custom From Scratch**
1. Select Custom Sort
2. Add 5 custom sections
3. Map files to sections
4. Export config
5. Exit and restart app
6. Import config
7. Verify sections and mappings loaded
8. Process files

**Scenario 3: Ignore Files**
1. Map 10 files
2. Ignore 3 files
3. Verify ignored files grayed out
4. Process files
5. Verify only 7 files in PDF
6. Check log for ignored files

**Scenario 4: Validation Errors**
1. Leave 2 files unmapped (not ignored)
2. Try to process
3. Verify error dialog appears
4. Verify log shows details
5. Fix mappings
6. Process successfully

**Scenario 5: Config Mismatch**
1. Create config with 15 files
2. Change input folder (10 files, 5 overlap)
3. Import config
4. Verify 5 matched, 5 unmapped
5. Map remaining files
6. Process successfully

---

## Migration from Old System

### For Existing Users

**Option 1: Fresh Start**
- Users start with new integrated system
- Old Excel files deprecated
- No migration needed

**Option 2: Excel Import Feature (Optional, Future)**
- Add "Import from Excel" button
- Read old Excel files → Convert to session state
- One-time migration
- Not essential for v1

**Recommendation:** Option 1 - Clean break, fresh start

### Deprecation Plan

**Old Files:**
- Keep `docs/filename_section.xlsx` as reference
- Add deprecation notice
- Remove in future version

**Old Code:**
- Keep Excel reading functions for now
- Mark as deprecated
- Remove when confident no one uses them

---

## Benefits of This Approach

### vs External Excel Files

✅ **No File Management**: No downloading, editing, uploading
✅ **Integrated Workflow**: Everything in one place
✅ **Immediate Feedback**: Real-time validation
✅ **Session-Based**: Work temporarily, export when satisfied
✅ **Less Error-Prone**: Dropdowns prevent typos
✅ **Better UX**: Professional, guided experience
✅ **Flexible**: Easy to adjust, no switching apps

### vs Static Templates

✅ **Auto-populated**: Files loaded automatically
✅ **Dynamic Dropdowns**: Always in sync
✅ **No Name Errors**: Files come from actual folder
✅ **Validation**: Multiple layers of checking
✅ **Reusable**: Export/import configs

---

## Known Limitations

⚠️ **Session-Only State**: Lost if app crashes (must export)
⚠️ **No Auto-Save**: User must remember to export
⚠️ **GUI Complexity**: More complex than simple form
⚠️ **Testing Effort**: More scenarios to test
⚠️ **Learning Curve**: Users need to understand new workflow

**Mitigations:**
- Clear documentation
- Helpful tooltips
- Good error messages
- Export reminders

---

## Future Enhancements (Not in Scope)

### Phase 10+: Nice-to-Have Features

1. **Template Library**
   - Save multiple named configs
   - Quick access to favorites
   - Share configs with team

2. **Undo/Redo**
   - For section edits
   - For file mappings

3. **Batch Operations**
   - Map multiple files at once
   - Bulk ignore/unignore

4. **Search/Filter**
   - Filter file list
   - Search sections

5. **Import from Excel**
   - Migrate old Excel files
   - One-time conversion

6. **Config Validation Tool**
   - Check config before import
   - Preview what will load

7. **Keyboard Shortcuts**
   - Fast navigation
   - Quick actions

8. **Drag & Drop**
   - Reorder sections
   - Drag files to sections

---

## Conclusion

This integrated approach provides a modern, professional user experience while maintaining flexibility for both ICH and custom use cases. The implementation is substantial but broken into manageable phases, allowing for incremental development and testing.

**Key Success Factors:**
- Clear phased approach
- Good separation of concerns
- Robust validation
- Excellent error handling
- Comprehensive testing

**Ready for Implementation!** 🚀

---

## Decision Checklist

Before proceeding, confirm:

- [x] Three sort modes: Default, ICH, Custom
- [x] Tabs within main window (show/hide)
- [x] Full CRUD for sections
- [x] Export config (no save, user chooses location)
- [x] JSON format
- [x] Dropdown validation
- [x] Ignore checkbox functionality
- [x] Real-time + pre-process validation
- [x] Session-based state
- [x] Default ICH config included
- [x] Files matched flexibly during import
- [x] No backward compatibility with Excel files

**All confirmed - ready to implement!**

