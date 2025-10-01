# RTF to PDF Converter with Table of Contents - User Guide

## Version 2.0 - Integrated Sort Feature

This tool converts RTF files to a single PDF document with an automatically generated table of contents and bookmarks.

---

## Table of Contents
1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Sort Modes](#sort-modes)
4. [Using Default Sort](#using-default-sort)
5. [Using ICH Sort](#using-ich-sort)
6. [Using Custom Sort](#using-custom-sort)
7. [Configuration Management](#configuration-management)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [Troubleshooting](#troubleshooting)

---

## Installation

### Requirements
- **Windows OS** (uses Microsoft Word COM automation)
- **Microsoft Word** installed
- **Python 3.6+** (for running from source)

### Running from Source
```bash
python -m venv .venv
venv\Scripts\activate
pip install -r requirements.txt
python run_gui.py
```

### Running from Executable
Simply run `RTF2PDF_GUI.exe` from the `dist` folder (after building).

---

## Quick Start

### Basic Workflow
1. Launch the application
2. Select input folder containing RTF files
3. Select output folder for generated PDF
4. Choose a sort mode (Default, ICH, or Custom)
5. Configure sections and file mappings (for ICH/Custom modes)
6. Click "Process Files"

---

## Sort Modes

### 1. Default Sort (Alphabetical)
- **Use Case**: Simple, quick processing without manual configuration
- **Behavior**: Files are processed in alphabetical order
- **Configuration**: None required
- **Best For**: Small projects or when order doesn't matter

### 2. ICH Sort (ICH E3 Sections)
- **Use Case**: Clinical study reports following ICH E3 guidelines
- **Behavior**: Pre-loaded with 15 ICH E3 sections
- **Configuration**: Map files to ICH sections, optionally modify sections
- **Best For**: Regulatory submissions, clinical trial reports

### 3. Custom Sort (User-Defined)
- **Use Case**: Projects with specific organizational requirements
- **Behavior**: Define your own section structure
- **Configuration**: Create sections, then map files
- **Best For**: Custom documents, non-ICH projects

---

## Using Default Sort

### Steps:
1. Select **"Default Sort (Alphabetical)"** radio button
2. Choose input and output folders
3. Set output filename
4. Configure PDF options (optional):
   - Page width (default: 210mm / A4)
   - Margins (default: 15mm)
   - Font sizes
   - Parallel workers (default: 3)
5. Click **"Process Files"** (F5)

### Notes:
- No file mapping required
- All RTF files in input folder are processed
- Files appear in alphabetical order in final PDF

---

## Using ICH Sort

### Step-by-Step Guide:

#### 1. Select ICH Sort Mode
- Click **"ICH Sort (ICH E3 Sections)"** radio button
- Configuration tab becomes available

#### 2. Review ICH Sections
- Switch to **Configuration tab**
- Go to **Section Definition** sub-tab
- Pre-loaded sections include:
  - 14 - Tables, Figures and Graphs
  - 14.1 - Demographic Data
  - 14.2 - Efficacy Data
  - 14.3 - Safety Data
  - 16.2 - Patient Data Listings
  - *...and more*

#### 3. Modify Sections (Optional)
- **Add Section**: Click "Add Section" button
- **Edit Section**: Double-click a section or select and click "Edit Selected"
- **Delete Section**: Select and click "Delete Selected"
- **Reset**: Click "Reset to ICH Defaults" to restore original sections

#### 4. Map Files to Sections
- Go to **File Mapping** sub-tab
- Files from input folder are auto-populated
- For each file:
  - **Double-click** the Section column
  - Select a section from the dropdown
  - Or **single-click** Ignore column to exclude file

#### 5. Review Status
- Check the summary bar: "Files: X | Mapped: Y | Ignored: Z | Unmapped: W"
- Ensure all files are either mapped or ignored
- Status indicators:
  - ✅ **Mapped** - File assigned to section
  - ⚠️ **Not Mapped** - No section assigned
  - 🚫 **Ignored** - File will be excluded

#### 6. Process Files
- Return to **Main tab**
- Click **"Process Files"** (F5)
- Monitor progress in log output

---

## Using Custom Sort

### Step-by-Step Guide:

#### 1. Select Custom Sort Mode
- Click **"Custom Sort (Define Your Own)"** radio button

#### 2. Define Sections
- Go to **Configuration tab** → **Section Definition**
- Click **"Add Section"**
- Enter:
  - **Section Number** (e.g., "1.1", "A.1", "Introduction")
  - **Section Label** (e.g., "Project Overview")
- Repeat for all sections

#### 3. Map Files
- Go to **File Mapping** sub-tab
- Double-click Section column for each file
- Select from your defined sections

#### 4. Process Files
- Validate all files are mapped
- Click **"Process Files"**

---

## Configuration Management

### Export Configuration
1. Click **"Export Config"** button (or Ctrl+S)
2. Choose save location
3. Default filename: `rtf2pdf_config_YYYYMMDD_HHMMSS.json`
4. Configuration includes:
   - Sort mode
   - Section definitions
   - File mappings
   - Metadata (date, version)

### Import Configuration
1. Click **"Import Config"** button (or Ctrl+I)
2. Select a JSON configuration file
3. Review import summary dialog:
   - Sections loaded
   - Files matched
   - Unmapped files
4. Adjust mappings for new files
5. Process as normal

### Configuration File Format
```json
{
  "version": "1.0",
  "sort_mode": "ich",
  "created_date": "2024-10-01T14:30:00",
  "project_name": "Study_ABC",
  "section_definitions": [
    {
      "section_number": "14.1",
      "section_label": "Demographic Data"
    }
  ],
  "file_mappings": [
    {
      "filename": "tsidm01",
      "section_number": "14.1",
      "ignore": false
    }
  ]
}
```

---

## Keyboard Shortcuts

### Global Shortcuts
| Shortcut | Action |
|----------|--------|
| **Ctrl+O** | Browse Input Folder |
| **Ctrl+I** | Import Configuration |
| **Ctrl+S** | Export Configuration |
| **F5** | Start Processing |
| **Escape** | Stop Processing |
| **F1** | Show Help |
| **F11** | Maximize Window |

### Configuration Tab
| Action | How To |
|--------|--------|
| Edit Section | Double-click section row |
| Edit File Mapping | Double-click Section column |
| Toggle Ignore | Single-click Ignore column |
| Save Dialog | Press Enter |
| Cancel Dialog | Press Escape |

---

## ICH E3 Sections Reference

Default ICH E3 sections included:

| Section | Name |
|---------|------|
| **14** | Tables, Figures and Graphs Referred to But Not Included in the Text |
| **14.1** | Demographic Data |
| **14.2** | Efficacy Data |
| **14.3** | Safety Data |
| **14.3.1** | Displays of Adverse Events |
| **14.3.2** | Listings of Deaths, Other Serious and Significant Adverse Events |
| **16.2** | Patient Data Listings |
| **16.2.1** | Discontinued patients |
| **16.2.2** | Protocol deviations |
| **16.2.3** | Patients excluded from the efficacy analysis |
| **16.2.4** | Demographic data |
| **16.2.5** | Compliance and/or drug concentration data |
| **16.2.6** | Individual efficacy response data |
| **16.2.7** | Adverse event listings (each patient) |
| **16.2.8** | Listing of individual laboratory measurements by patient |

---

## PDF Options

### Configurable Settings
- **Page Width**: Default 210mm (A4 size)
- **Margins**: Default 15mm
- **Font Size**: Default 8pt
- **Header Font Size**: Default 10pt
- **Parallel Workers**: Number of simultaneous RTF conversions (1-10, default 3)

### Output Structure
```
output/
├── _pdf/                           # Individual PDF files
│   ├── file1.pdf
│   ├── file2.pdf
│   └── ...
└── final_document_with_toc.pdf    # Combined PDF with TOC
```

---

## Troubleshooting

### Issue: "No RTF files found"
**Solution**: Check that input folder contains `.rtf` files

### Issue: "Validation Errors - Unmapped files"
**Solution**:
- Go to Configuration → File Mapping
- Map all files to sections OR
- Check Ignore checkbox for files to exclude

### Issue: "Microsoft Word not found"
**Solution**:
- Ensure Microsoft Word is installed
- Run application as administrator
- Close any open Word instances

### Issue: "Configuration import failed"
**Solution**:
- Verify JSON file is not corrupted
- Check file was exported from this application
- Ensure all required fields are present

### Issue: "Process stopped unexpectedly"
**Solution**:
- Check log output for error details
- Verify file permissions
- Ensure RTF files are not corrupted
- Check available disk space

### Issue: "Some files failed to convert"
**Solution**:
- Check log for specific file errors
- Try converting problematic files individually
- Verify files are valid RTF format
- Check if files are password-protected or locked

---

## Tips & Best Practices

### For ICH Sort:
1. **Review pre-loaded sections** - Add missing subsections if needed
2. **Use consistent naming** - Match your file naming convention
3. **Export configuration** - Save for future similar projects
4. **Validate before processing** - Check summary statistics

### For Custom Sort:
1. **Plan section structure first** - Define all sections before mapping
2. **Use hierarchical numbering** - e.g., 1.1, 1.2, 2.1 for clarity
3. **Keep labels descriptive** - Helps with quick identification
4. **Test with small dataset** - Verify structure before full run

### General:
1. **Use parallel workers wisely** - More workers = faster but more memory
2. **Close Word before processing** - Prevents COM automation issues
3. **Backup important files** - Keep originals safe
4. **Monitor log output** - Catch errors early
5. **Regular exports** - Save configurations for reproducibility

---

## Support

For issues or questions:
- Check the log output for detailed error messages
- Review this guide for common solutions
- Check CLAUDE.md for development information

---

**Version**: 2.0
**Last Updated**: October 2024
**© 2024 - RTF to PDF Converter**