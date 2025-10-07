# RTF to PDF Converter with TOC

A Python application that converts RTF files to PDF and combines them into a single PDF document with a table of contents and bookmarks.

## Features

### Core Functionality
- Convert multiple RTF files to PDF
- Generate table of contents with page numbers and clickable hyperlinks
- Create hierarchical PDF bookmarks for easy navigation
- Modern GUI interface with progress tracking
- Configurable PDF settings
- Real-time conversion progress
- Detailed logging
- Smart file organization by type (Tables, Figures, Listings)
- Automatic temporary file cleanup

### Version 3.0 Features
- **Three Sort Modes**: Default (automatic), ICH E3, or Custom sections
- **Pattern-Based File Mapping**: Map 50+ files in seconds using regex/wildcard patterns
  - Quick Pattern assignment with live preview
  - Reusable pattern rules with priority-based conflict resolution
  - Pattern templates for common use cases
- **Bulk Section Import**: Import section definitions from Excel files
  - Validate before import with preview mode
  - Conflict detection and handling
  - Sample template generator
- **Configuration Management**: Export/import complete configurations (sections, mappings, pattern rules)
- **Interactive File Mapping**: Assign files to sections with dropdown selection or pattern matching

## Requirements

- Windows OS (uses Word COM automation)
- Python 3.6 or higher
- Microsoft Word installed
- Required Python packages (install via `pip install -r requirements.txt`):
  - pandas
  - fpdf2
  - pypdf
  - PyMuPDF (fitz)
  - pywin32

## Installation

1. Clone the repository:
```bash
git clone https://github.com/vikasgaddu1/rtf2pdfCombineWithToc.git
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

1. Launch the GUI:
```bash
python run_gui.py
```

2. Configure the settings in the GUI:
   - **Input Folder**: Select the folder containing RTF files
   - **Output Folder**: Choose where to save the generated PDFs
   - **Output Filename**: Name for the final combined PDF
   - **Sort Mode**: Choose from three organizational modes:
     - **Default Sort**: Automatic alphabetical organization by prefix (t→Tables, f→Figures, l→Listings)
     - **ICH Sort**: Organize using ICH E3 clinical study report sections
     - **Custom Sort**: Define your own custom sections
   - **PDF Options**:
     - Page Width (mm): Default 210 (A4)
     - Margin (mm): Default 15
     - Font Size: Default 8
     - Header Font Size: Default 10
     - Parallel Workers: Number of simultaneous RTF conversions

3. Click "▶ Process Files" to start the conversion

### Sort Modes

#### Default Sort (Automatic)
Files are automatically organized based on their filename prefixes:
- `t*`: Tables (Section 1)
- `f*`: Figures (Section 2)
- `l*`: Listings (Section 3)

Within each section, files are sorted alphabetically. No configuration needed - fully automatic!

#### ICH Sort (ICH E3 Sections)
Organize files according to ICH E3 clinical study report structure with 15 pre-defined sections:
- 14.1 Study Demographics
- 14.2 Drug Exposure
- 14.3 Efficacy Analysis
- ...and 12 more ICH E3 sections

**Smart Sorting**: Within each section, files are automatically sorted by type:
1. Tables (t*) - alphabetically
2. Figures (f*) - alphabetically
3. Listings (l*) - alphabetically

Use the **Configuration** tab to:
- View all ICH sections in the Section Definition tab
- Assign files to sections in the File Mapping tab
- Mark files to ignore
- Import/Export configurations for reuse

#### Custom Sort (User-Defined)
Create your own section structure for maximum flexibility:

1. Switch to **Custom Sort** mode
2. Go to the **Configuration** tab
3. In the **Section Definition** tab:
   - Click "Add Section" to create custom sections manually
   - OR click "📊 Import from Excel" to bulk import sections from Excel file
   - Define section numbers (e.g., "1.1", "2.3")
   - Define section labels (e.g., "Introduction", "Results")
4. In the **File Mapping** tab:
   - **Manual Assignment**: Click a file's Section column to assign it
   - **Pattern-Based Mapping**: Use "⚡ Quick Pattern" to map multiple files at once
     - Select files with similar names
     - Click "Quick Pattern" button
     - Auto-suggest or enter a regex/wildcard pattern
     - Preview matches and apply to all matching files
   - **Batch Operations**: Use "📋 Manage Rules" to create reusable pattern rules
   - Click the checkbox to ignore files
5. Save your configuration using "📤 Export Configuration" on Main tab for reuse

**Smart Sorting**: Like ICH mode, files within each custom section are automatically sorted by type (Tables → Figures → Listings), then alphabetically within each type.

### New in Version 3.0

#### Pattern-Based File Mapping
Map multiple files to sections in seconds:
- **Quick Pattern**: Select files → Get pattern suggestion → Apply to all matches
- **Pattern Rules**: Create reusable rules with priorities for future projects
- **Templates**: Built-in regex and wildcard pattern examples
- **Live Preview**: See which files match before applying

Example: Map all files starting with "fslb" to Section 14.3.1 using pattern `^fslb.*`

#### Bulk Section Import
Import sections from Excel instead of typing manually:
- Required columns: `section_number` and `section_label`
- Preview import before committing
- Conflict detection with existing sections
- Download sample template to get started

Example: Import 15 ICH E3 sections from Excel in 10 seconds

#### Configuration Management
All configurations now include:
- Section definitions
- File mappings (which file goes to which section)
- Pattern rules (for reusable pattern-based mapping)
- Located on **Main tab** for easy access

### Output

The application generates:
1. Individual PDF files in the `output/_pdf/` subfolder
2. A combined PDF with:
   - Clickable table of contents with hyperlinks to each document
   - Hierarchical bookmarks matching TOC structure
   - Smart file ordering (Tables → Figures → Listings within each section)
3. Temporary files in `output/_temp/` (automatically cleaned up after processing)
4. Log output in the GUI showing conversion progress

**File Locking Handling**: If the output PDF is open in another program, the application will:
- Prompt you to close the file and retry
- OR let you choose a different filename/location via a "Save As" dialog

## Building Executable

This project includes a PowerShell build script that creates standalone executable files for both GUI and CLI versions of the application using PyInstaller.

### Prerequisites

1. Ensure you have a virtual environment set up with all dependencies installed:
```bash
python -m venv .venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Make sure PowerShell execution policy allows running scripts:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Running the Build Script

1. **Open PowerShell** in the project root directory

2. **Run the build script**:
```powershell
.\build.ps1
```

The build script will:
- Check if the virtual environment exists
- Activate the virtual environment automatically
- Verify Python and pip are available from the venv
- Install/update all dependencies
- Build both GUI and CLI executables using PyInstaller
- Deactivate the virtual environment when complete

### Build Output

After successful completion, you'll find the executables in the `dist` folder:
- `RTF2PDF_GUI.exe` - Graphical user interface version
- `RTF2PDF_CLI.exe` - Command-line interface version

### Notes

- The build process may show warnings about missing libraries (api-ms-win-crt-*.dll), but these are typically non-critical and the executables will still function properly
- Make sure to copy the `docs` folder alongside the executables if your application requires it
- The first build may take several minutes as PyInstaller analyzes all dependencies

### Troubleshooting Build Issues

1. **Execution Policy Error**: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force`
2. **Virtual Environment Not Found**: Ensure the `venv` folder exists in the project root
3. **PyInstaller Errors**: Check that all dependencies are installed correctly in the virtual environment

## Project Structure

```
rtf2pdfcombine/
├── run_gui.py                      # GUI launcher
├── main.py                         # Main processing logic
├── requirements.txt                # Python dependencies
├── input/                          # Input RTF files
├── output/                         # Generated PDFs
│   ├── _pdf/                      # Individual converted PDFs
│   ├── _temp/                     # Temporary files (auto-cleaned)
│   └── final_document_with_toc.pdf  # Final combined PDF
├── config/                         # Exported configuration files
├── docs/                           # Documentation
│   ├── USER_GUIDE.md              # Comprehensive user guide
│   ├── PATTERN_MAPPING_USER_GUIDE.md  # Pattern-based mapping guide
│   └── iche3_categories.xlsx      # ICH E3 section definitions
└── src/
    ├── gui.py                     # GUI implementation
    ├── gui_config.py              # Configuration holder
    ├── session_state.py           # Session state management
    ├── pattern_rules.py           # Pattern matching logic
    ├── pattern_dialogs.py         # Pattern UI dialogs
    ├── bulk_section_import.py     # Excel section import logic
    ├── bulk_import_dialog.py      # Bulk import UI dialog
    ├── rtf_converter.py           # RTF to PDF conversion
    ├── rtf_parser.py              # RTF title extraction
    ├── data_processing.py         # Data handling and validation
    └── pdf_utils.py               # PDF generation utilities
```

## GUI Settings

All application settings are configured through the GUI interface:

- **Input/Output Paths**: Browse and select folders directly
- **Section Mode**: Toggle between automatic and manual modes
- **PDF Settings**: Adjust page layout and font sizes
- **No Configuration Files**: All settings are passed directly from the GUI to the processing engine

## Additional Documentation

- **[User Guide](docs/USER_GUIDE.md)**: Comprehensive step-by-step guide for all features
- **[Pattern Mapping Guide](docs/PATTERN_MAPPING_USER_GUIDE.md)**: Detailed guide for pattern-based file mapping with examples

## Troubleshooting

1. **Word COM Automation Issues**
   - Ensure Microsoft Word is installed
   - Close any open Word instances
   - Run the application with administrator privileges
   - Check if Word is properly registered in the system

2. **File Conversion Failures**
   - Check file permissions
   - Verify RTF files are not corrupted
   - Ensure filenames follow the required format
   - Check if the output directory is writable

3. **Section Mapping Issues**
   - For Excel import: Ensure columns are named `section_number` and `section_label`
   - For pattern rules: Use "Test Pattern" to verify your regex/wildcard patterns
   - Check section numbers match ICH categories (for ICH mode)
   - Ensure filenames match exactly

4. **Pattern Matching Issues**
   - Use "Preview" in Quick Pattern dialog to test patterns before applying
   - Regex mode is case-insensitive by default
   - Common patterns: `^f.*` (starts with f), `.*01.*` (contains 01), `.*_ae$` (ends with _ae)
   - See Pattern Mapping Guide for more examples

5. **TOC/Bookmark Issues**
   - Hyperlinks in TOC are clickable - ensure you're clicking on the blue text
   - Bookmarks appear in the left panel (may need to open bookmarks pane in PDF reader)
   - Files are sorted by type (Tables/Figures/Listings) within each section automatically
   - TOC order matches PDF page order and bookmark hierarchy

6. **Output File Locked**
   - Close the PDF in your PDF reader before running again
   - Use "Save As" dialog to save to a different location
   - Check file permissions if save fails

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your License Here]

## Acknowledgments

- Microsoft Word COM automation
- FPDF2 for PDF generation
- PyMuPDF for PDF manipulation
