# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the Application
- **GUI mode**: `python run_gui.py`
- **CLI mode**: `python main.py` (with GUIConfig configured)

### Building Executables
- **PowerShell**: `.\build.ps1`
- **Batch file**: `build.bat`
- Builds both GUI and CLI executables using PyInstaller
- Output executables: `dist\RTF2PDF_GUI.exe` and `dist\RTF2PDF_CLI.exe`

### Virtual Environment Setup
```bash
python -m venv .venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Testing
- **Run tests**: `pytest` (tests need to be created)

## Architecture Overview

### Core Application Flow
The application converts RTF files to PDF and combines them with a table of contents:

1. **RTF Title Extraction** (`src/rtf_parser.py`): Extracts titles from RTF files using striprtf
2. **Data Processing** (`src/data_processing.py`):
   - Handles section mapping (automatic or manual via Excel)
   - Validates files against ICH categories
   - Creates TOC structure
3. **RTF to PDF Conversion** (`src/rtf_converter.py`):
   - Uses Windows COM automation with Microsoft Word
   - Thread-safe Word instance management
   - Converts RTF files to individual PDFs
4. **PDF Generation** (`src/pdf_utils.py`):
   - Generates TOC PDF using FPDF2
   - Combines PDFs using PyPDF
   - Adds bookmarks using PyMuPDF

### Key Components

- **`main.py`**: Main processing logic, coordinates all steps
- **`run_gui.py`**: GUI launcher entry point
- **`src/gui.py`**: Tkinter-based GUI implementation with progress tracking
- **`src/gui_config.py`**: Configuration management for GUI settings
- **`src/rtf_converter.py`**: Windows-specific RTF→PDF conversion using Word COM
- **`src/rtf_parser.py`**: RTF title extraction without Word dependency
- **`src/data_processing.py`**: Data validation, section mapping, TOC structure
- **`src/pdf_utils.py`**: PDF generation, combination, and bookmark management

### Section Organization Modes

1. **Automatic Mode**: Files organized by prefix:
   - `t*` → Tables (Section 1)
   - `f*` → Figures (Section 2)
   - `l*` → Listings (Section 3)

2. **Manual Mode**: Uses Excel file (`docs/filename_section.xlsx`) with:
   - `filename`: RTF filename without extension
   - `section_number`: Section identifier
   - `section_label`: Section name (generic, works for both ICH and Custom modes)

### Important Dependencies

- **Windows-only**: Requires Microsoft Word for RTF conversion
- **COM Automation**: Uses pywin32 for Word integration
- **PDF Libraries**: FPDF2 (generation), PyPDF (merging), PyMuPDF (bookmarks)
- **Data Processing**: pandas, openpyxl for Excel handling

### File Organization

- `input/`: RTF source files
- `output/`: Generated PDFs
  - `_pdf/`: Individual converted PDFs
- `docs/`: Configuration files (Excel mappings)
- `dist/`: Built executables (after build)

## Development Notes

### Windows COM Considerations
- Application closes Word processes before starting to prevent conflicts
- Uses thread-local storage for Word instances in multi-threaded scenarios
- Implements proper COM cleanup to prevent memory leaks

### Error Handling
- Comprehensive logging throughout the conversion process
- Graceful degradation when optional libraries unavailable (e.g., PyMuPDF)
- Validation of Excel mapping files with mismatch reporting

### GUI Features
- Real-time progress tracking with percentage and status updates
- Configurable PDF settings (page size, margins, fonts)
- Thread-based processing to prevent UI freezing
- Stop functionality to cancel long-running operations