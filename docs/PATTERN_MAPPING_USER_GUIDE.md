# Pattern-Based Section Mapping - User Guide

## Overview

Pattern-based section mapping is a powerful feature that allows you to automatically assign multiple files to sections using patterns (regex or wildcards) instead of clicking on each file individually.

**Key Benefits:**
- Map 50+ files in seconds instead of minutes
- Create reusable rules for consistent project setups
- Reduce errors from repetitive manual assignments
- Mix automatic patterns with manual overrides

## When to Use Pattern Rules

Pattern rules are ideal when you have:
- Many files with similar naming patterns (e.g., `fslb01a`, `fslb01b`, `fslb02a`)
- Repeating projects with consistent file naming conventions
- Files organized by prefix, suffix, or category codes
- Large datasets where manual mapping is time-consuming

## Getting Started

### Prerequisites

1. **Switch to ICH or Custom Mode**
   - Pattern rules are only available in ICH or Custom sort modes
   - Go to Main tab and select "ICH Sort" or "Custom Sort"

2. **Define Sections**
   - For ICH mode: Sections are pre-loaded automatically
   - For Custom mode: Define your sections in the Section Definition tab

3. **Load Your Files**
   - Select your input folder containing RTF files
   - Files will appear in the File Mapping tab

## Using Pattern Rules - Three Ways

### Method 1: Quick Pattern (Recommended for Beginners)

**Best for:** One-time assignments or learning patterns

1. **Select files** in the File Mapping tab (optional but recommended)
2. Click **"⚡ Quick Pattern"** button
3. Click **"Suggest"** to auto-generate a pattern from your selection
4. **Test the pattern** to see which files it matches
5. **Select target section** from dropdown
6. Check **"Save as permanent rule"** if you want to reuse it
7. Click **"Apply to Matched Files"**

**Example:**
- Selected files: `fslb01a`, `fslb01b`, `fslb02a`
- Suggested pattern: `^fslb.*`
- Matches: All 12 files starting with "fslb"
- Assign to: Section 14.3.1

### Method 2: Manage Rules (For Advanced Users)

**Best for:** Creating multiple reusable rules with priorities

1. Click **"📋 Manage Rules"** button
2. Click **"➕ Add Rule"** to create a new rule
3. Enter pattern (use templates for help)
4. Select section and set priority
5. Test the pattern to verify matches
6. Save the rule

**Rule Priority:**
- Higher priority numbers override lower ones
- Example: If file `fslb01a` matches both:
  - `^fslb.*` (priority 10) → Section 14.3.1
  - `^fslb01.*` (priority 20) → Section 14.3.2
- Winner: Priority 20 rule → Section 14.3.2

### Method 3: Apply All Rules

**Best for:** Applying saved rules to new files

1. Load your configuration (File → Import Configuration)
2. Load new RTF files
3. Click **"▶ Apply All Rules"**
4. Choose whether to override existing mappings
5. Review the results

## Pattern Syntax

### Regex Patterns (Default)

| Pattern | Matches | Example |
|---------|---------|---------|
| `^fslb.*` | Files starting with "fslb" | fslb01, fslb02a, fslb_test |
| `.*_ae$` | Files ending with "_ae" | report_ae, summary_ae |
| `.*adverse.*` | Files containing "adverse" | adverse_events, drug_adverse |
| `^[a-z]+\d{2}[a-z]?$` | Letter(s) + 2 digits + optional letter | fslb01, tsid02a, dm03 |
| `^(ae\|cm\|dm).*` | Files starting with ae, cm, or dm | ae01, cm02, dm03 |

### Wildcard Patterns (Simple)

| Pattern | Matches | Example |
|---------|---------|---------|
| `fslb*` | Files starting with "fslb" | fslb01, fslb_test |
| `*_ae` | Files ending with "_ae" | report_ae, summary_ae |
| `*adverse*` | Files containing "adverse" | adverse_events |
| `*_v?_final` | Version pattern | data_v1_final, data_v2_final |

**Note:** Regex is more powerful but requires escaping special characters. Wildcards are simpler but less flexible.

## Real-World Examples

### Example 1: Clinical Trial Listings

**Scenario:** 50 files for adverse events, all named `fslb01a` through `fslb25b`

**Solution:**
1. Create rule: `^fslb.*` → Section 14.3.1
2. Apply rule
3. All 50 files mapped in seconds ✓

### Example 2: Multiple Categories

**Scenario:** Files organized by category codes:
- `ae*` files → Section 14.3 (Adverse Events)
- `cm*` files → Section 14.2 (Efficacy)
- `dm*` files → Section 16.2 (Demographics)

**Solution:**
1. Create 3 rules:
   - `^ae.*` → 14.3 (priority 10)
   - `^cm.*` → 14.2 (priority 10)
   - `^dm.*` → 16.2 (priority 10)
2. Apply all rules
3. All files categorized automatically ✓

### Example 3: Override for Specific Files

**Scenario:** Most `fslb*` files go to 14.3.1, but `fslb01*` files are special and go to 14.3.2

**Solution:**
1. Create two rules:
   - `^fslb.*` → 14.3.1 (priority 10) - catches all fslb files
   - `^fslb01.*` → 14.3.2 (priority 20) - overrides for fslb01 files
2. Apply rules
3. Priority system handles the exception ✓

### Example 4: Version Control

**Scenario:** Only include final versions, exclude drafts

**Solution:**
1. Create rule: `.*_final$` → 16.2
2. Files not matching are left unmapped
3. Manually review unmapped files
4. Mark drafts as "Ignore" ✓

## Pattern Templates

The Quick Pattern dialog includes built-in templates:

1. **Files starting with prefix** - `^prefix.*`
2. **Files ending with suffix** - `.*suffix$`
3. **Files containing text** - `.*text.*`
4. **Numbered sequence** - `^[a-z]+\d{2}[a-z]?$`
5. **Category prefixes** - `^(ae|cm|dm).*`
6. **Wildcard pattern** - `prefix*`
7. **Multiple wildcards** - `*_v*_final`

Select a template to auto-fill the pattern field, then customize as needed.

## Saving and Reusing Rules

### Export Configuration

1. File → Export Configuration
2. Save as JSON file
3. Includes all pattern rules, sections, and mappings

### Import Configuration

1. File → Import Configuration
2. Select your saved JSON file
3. Pattern rules are automatically loaded
4. Apply rules to new files with one click

**Tip:** Create a "template" configuration for each project type and reuse it.

## Troubleshooting

### Pattern Doesn't Match Expected Files

**Check:**
- Regex vs Wildcard mode selection
- Special characters need escaping in regex (e.g., `\.` for literal dot)
- Use "Test Pattern" to preview matches before applying
- File names are case-insensitive by default

**Solution:** Use the pattern templates as a starting point and modify incrementally.

### Multiple Rules Matching Same File

**This is normal!** The highest priority rule wins.

**To control:**
1. Set priorities intentionally (higher = more specific)
2. Use Manage Rules dialog to review all rules
3. Test with specific files to verify behavior

### Rules Not Applying

**Check:**
1. Are you in ICH or Custom mode? (Not Default mode)
2. Are sections defined?
3. Are rules marked as "Active"?
4. Use "Apply All Rules" button to trigger application

## Best Practices

1. **Start Simple**
   - Begin with Quick Pattern for learning
   - Progress to Manage Rules as you gain confidence

2. **Test Before Applying**
   - Always use "Test Pattern" to preview matches
   - Verify the count matches your expectation

3. **Use Meaningful Priorities**
   - General rules: priority 10
   - Category rules: priority 20
   - Specific exceptions: priority 30+

4. **Document Your Rules**
   - Use the "Description" field to explain each rule
   - Helps team members understand the logic

5. **Combine with Manual Mapping**
   - Use patterns for bulk assignment
   - Manually adjust exceptions as needed
   - Pattern rules won't override manual changes (unless you choose to)

6. **Save Configurations**
   - Export configs for each project type
   - Share with team members for consistency

## Keyboard Shortcuts

While in File Mapping tab:
- **Ctrl+Shift+P** - Open Quick Pattern (if enabled)
- **Tab** - Move to next file
- **Space** - Toggle ignore status

## Tips and Tricks

1. **Pattern from Selection**
   - Select 2-3 representative files
   - Click "Suggest" in Quick Pattern
   - Often gives you the exact pattern you need

2. **Incremental Refinement**
   - Start with broad pattern (e.g., `^fs.*`)
   - Test and see matches
   - Refine to be more specific (e.g., `^fslb.*`)

3. **Leave Some Unmapped**
   - Not every file needs a pattern rule
   - Use patterns for the bulk, manual map the exceptions
   - More maintainable than complex pattern logic

4. **Version in Filename**
   - Consider including version in filename
   - Pattern: `.*_v\d+_.*` matches `report_v1_final.rtf`, `report_v2_final.rtf`

5. **Test on Small Subset First**
   - Work with 10-20 files initially
   - Perfect your patterns
   - Apply to full dataset when confident

## Need Help?

- **Pattern Regex Tester:** Use online tools like regex101.com to test patterns
- **Examples:** Check `test_pattern_rules.py` for working code examples
- **Implementation Details:** See `docs/PATTERN_BASED_MAPPING_IMPLEMENTATION.md`

---

**Version:** 3.0
**Feature Status:** Fully Implemented (Phase 1 & 2)
**Last Updated:** 2025-10-02
