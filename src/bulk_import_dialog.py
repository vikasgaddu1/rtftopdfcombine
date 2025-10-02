"""
UI dialog for bulk section import from Excel.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import logging
from src.bulk_section_import import BulkSectionImporter, import_sections_from_excel


class BulkSectionImportDialog:
    """Dialog for importing sections in bulk from Excel."""

    def __init__(self, parent, session_state):
        self.parent = parent
        self.session_state = session_state
        self.importer = BulkSectionImporter()
        self.selected_file = None
        self.import_result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Bulk Import Sections from Excel")
        self.dialog.geometry("800x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_window()

    def _center_window(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title and instructions
        title_label = ttk.Label(main_frame, text="Import Section Definitions from Excel",
                               font=("Segoe UI", 12, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 10))

        instructions = ttk.Label(main_frame,
                                text="Select an Excel file containing 'section_number' and 'section_label' columns.\n"
                                     "Conflicting entries will be detected and reported.",
                                font=("Segoe UI", 9))
        instructions.pack(anchor=tk.W, pady=(0, 15))

        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="Select Excel File", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly', width=60)
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_btn = ttk.Button(file_frame, text="Browse...", command=self._browse_file)
        browse_btn.pack(side=tk.LEFT, padx=(0, 5))

        download_template_btn = ttk.Button(file_frame, text="Download Template",
                                          command=self._download_template)
        download_template_btn.pack(side=tk.LEFT)

        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Import Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        self.skip_conflicts_var = tk.BooleanVar(value=True)
        skip_check = ttk.Checkbutton(options_frame,
                                     text="Skip conflicting entries (recommended)",
                                     variable=self.skip_conflicts_var)
        skip_check.pack(anchor=tk.W)

        help_label = ttk.Label(options_frame,
                              text="If unchecked, import will fail if any conflicts are detected.",
                              font=("Segoe UI", 8, "italic"),
                              foreground="#666")
        help_label.pack(anchor=tk.W, padx=(20, 0))

        # Preview/Results frame
        preview_frame = ttk.LabelFrame(main_frame, text="Preview / Results", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Status label
        self.status_label = ttk.Label(preview_frame, text="Select an Excel file to preview...",
                                     font=("Segoe UI", 9))
        self.status_label.pack(anchor=tk.W, pady=(0, 5))

        # Results text area with scrollbar
        text_frame = ttk.Frame(preview_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_text = tk.Text(text_frame, height=15, wrap=tk.WORD,
                                    yscrollcommand=scrollbar.set, state='disabled')
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.results_text.yview)

        # Configure text tags for colored output
        self.results_text.tag_config("success", foreground="#28a745")
        self.results_text.tag_config("error", foreground="#dc3545")
        self.results_text.tag_config("warning", foreground="#ffc107")
        self.results_text.tag_config("info", foreground="#0066cc")
        self.results_text.tag_config("header", font=("Segoe UI", 9, "bold"))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.preview_btn = ttk.Button(button_frame, text="Preview Import",
                                      command=self._preview_import, state='disabled')
        self.preview_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.import_btn = ttk.Button(button_frame, text="Import Sections",
                                     command=self._import_sections, state='disabled')
        self.import_btn.pack(side=tk.LEFT, padx=(0, 5))

        close_btn = ttk.Button(button_frame, text="Close", command=self.dialog.destroy)
        close_btn.pack(side=tk.RIGHT)

    def _browse_file(self):
        """Browse for Excel file."""
        file_path = filedialog.askopenfilename(
            parent=self.dialog,
            title="Select Excel File",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            self.selected_file = Path(file_path)
            self.file_path_var.set(str(self.selected_file))
            self.preview_btn.config(state='normal')
            self._clear_results()
            self._show_message("File selected. Click 'Preview Import' to validate.", "info")

    def _download_template(self):
        """Download a sample Excel template."""
        save_path = filedialog.asksaveasfilename(
            parent=self.dialog,
            title="Save Template As",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="section_import_template.xlsx"
        )

        if save_path:
            try:
                self.importer.create_sample_excel(Path(save_path), include_example_data=True)
                messagebox.showinfo("Template Created",
                                  f"Sample template created successfully:\n{save_path}\n\n"
                                  f"The template includes example data that you can replace.",
                                  parent=self.dialog)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create template: {str(e)}",
                                   parent=self.dialog)

    def _clear_results(self):
        """Clear the results text area."""
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state='disabled')

    def _show_message(self, message: str, tag: str = "info"):
        """Show a message in the results area."""
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, message + "\n", tag)
        self.results_text.config(state='disabled')

    def _append_result(self, text: str, tag: str = "info"):
        """Append text to the results area."""
        self.results_text.config(state='normal')
        self.results_text.insert(tk.END, text + "\n", tag)
        self.results_text.config(state='disabled')

    def _preview_import(self):
        """Preview what will be imported without actually importing."""
        if not self.selected_file:
            messagebox.showwarning("No File Selected",
                                  "Please select an Excel file first.",
                                  parent=self.dialog)
            return

        self._clear_results()
        self.status_label.config(text="Validating and previewing...")

        try:
            # Validate file
            is_valid, error_msg = self.importer.validate_excel_file(self.selected_file)
            if not is_valid:
                self.status_label.config(text="Validation failed")
                self._show_message(f"❌ Validation Error:\n{error_msg}", "error")
                return

            # Read sections
            success, sections, errors = self.importer.read_sections_from_excel(self.selected_file)
            if not success:
                self.status_label.config(text="Failed to read file")
                self._show_message(f"❌ Error reading Excel file:\n" + "\n".join(errors), "error")
                return

            # Detect conflicts
            conflicts = self.importer.detect_conflicts(sections, self.session_state.section_definitions)

            # Display results
            self._clear_results()
            self._append_result("=== IMPORT PREVIEW ===", "header")
            self._append_result(f"File: {self.selected_file.name}", "info")
            self._append_result("")

            self._append_result(f"📊 Found {len(sections)} section(s) in Excel file:", "header")
            for section_num, section_label in sections[:10]:  # Show first 10
                self._append_result(f"  • {section_num}: {section_label}", "info")
            if len(sections) > 10:
                self._append_result(f"  ... and {len(sections) - 10} more", "info")
            self._append_result("")

            if errors:
                self._append_result(f"⚠️ Found {len(errors)} error(s) in Excel:", "warning")
                for error in errors[:5]:
                    self._append_result(f"  • {error}", "warning")
                if len(errors) > 5:
                    self._append_result(f"  ... and {len(errors) - 5} more", "warning")
                self._append_result("")

            if conflicts:
                self._append_result(f"⚠️ Found {len(conflicts)} conflict(s) with existing sections:", "warning")
                for conflict in conflicts[:10]:
                    self._append_result(
                        f"  • {conflict['section_number']}: "
                        f"Existing='{conflict['existing_label']}' vs New='{conflict['new_label']}'",
                        "warning"
                    )
                if len(conflicts) > 10:
                    self._append_result(f"  ... and {len(conflicts) - 10} more", "warning")
                self._append_result("")

                if self.skip_conflicts_var.get():
                    self._append_result(f"✓ These {len(conflicts)} conflicting entries will be SKIPPED", "info")
                else:
                    self._append_result(f"❌ Import will FAIL due to conflicts (uncheck 'Skip conflicts' to import)", "error")
                self._append_result("")

            # Calculate what will be imported
            new_count = len(sections) - len(conflicts)
            self._append_result(f"📥 Import Summary:", "header")
            self._append_result(f"  • Will import: {new_count} new section(s)", "success")
            self._append_result(f"  • Will skip: {len(conflicts)} conflicting section(s)", "warning")
            self._append_result(f"  • Errors: {len(errors)} invalid row(s)", "error" if errors else "info")

            if new_count > 0:
                self._append_result("\n✓ Ready to import! Click 'Import Sections' to proceed.", "success")
                self.import_btn.config(state='normal')
                self.status_label.config(text=f"Preview complete: {new_count} sections ready to import")
            else:
                self._append_result("\n⚠️ No new sections to import (all are conflicts or errors)", "warning")
                self.import_btn.config(state='disabled')
                self.status_label.config(text="No new sections to import")

        except Exception as e:
            logging.error(f"Error during preview: {e}")
            self.status_label.config(text="Preview failed")
            self._show_message(f"❌ Unexpected error during preview:\n{str(e)}", "error")

    def _import_sections(self):
        """Actually perform the import."""
        if not self.selected_file:
            messagebox.showwarning("No File Selected",
                                  "Please select an Excel file first.",
                                  parent=self.dialog)
            return

        # Confirm import
        if not messagebox.askyesno("Confirm Import",
                                  "Import sections from Excel file?\n\n"
                                  "This will add new sections to your configuration.",
                                  parent=self.dialog):
            return

        self._clear_results()
        self.status_label.config(text="Importing sections...")

        try:
            # Log session state before import
            before_count = len(self.session_state.section_definitions)
            logging.info(f"Before import: {before_count} sections in session state")

            # Perform import
            result = import_sections_from_excel(
                self.selected_file,
                self.session_state,
                skip_conflicts=self.skip_conflicts_var.get()
            )

            # Log session state after import
            after_count = len(self.session_state.section_definitions)
            logging.info(f"After import: {after_count} sections in session state")
            if after_count > 0:
                logging.info(f"Sample sections: {[(s.section_number, s.section_label) for s in self.session_state.section_definitions[:3]]}")

            # Display results
            self._clear_results()
            self._append_result("=== IMPORT RESULTS ===", "header")
            self._append_result("")

            if result.success:
                self._append_result(f"✓ Import completed successfully!", "success")
                self._append_result("")
                self._append_result(f"📊 Summary:", "header")
                self._append_result(f"  • Imported: {result.imported_count} section(s)", "success")
                self._append_result(f"  • Skipped: {result.skipped_count} conflicting section(s)", "warning")
                self._append_result(f"  • Errors: {result.error_count} invalid row(s)", "error" if result.errors else "info")
                self._append_result("")

                if result.conflicts:
                    self._append_result(f"⚠️ Skipped {len(result.conflicts)} conflicting entries:", "warning")
                    for conflict in result.conflicts[:5]:
                        self._append_result(f"  • {conflict['section_number']}", "warning")
                    if len(result.conflicts) > 5:
                        self._append_result(f"  ... and {len(result.conflicts) - 5} more", "warning")
                    self._append_result("")

                if result.errors:
                    self._append_result(f"⚠️ Encountered {len(result.errors)} error(s):", "warning")
                    for error in result.errors[:5]:
                        self._append_result(f"  • {error}", "warning")
                    if len(result.errors) > 5:
                        self._append_result(f"  ... and {len(result.errors) - 5} more", "warning")
                    self._append_result("")

                self._append_result(f"✓ Your session now has {len(self.session_state.section_definitions)} total section(s)", "success")
                self.status_label.config(text=f"Import complete: {result.imported_count} sections added")

                # Store result for parent to refresh UI
                self.import_result = result

            else:
                self._append_result(f"❌ Import failed!", "error")
                self._append_result("")
                for error in result.errors:
                    self._append_result(f"  • {error}", "error")
                self.status_label.config(text="Import failed")

        except Exception as e:
            logging.error(f"Error during import: {e}")
            self.status_label.config(text="Import failed")
            self._show_message(f"❌ Unexpected error during import:\n{str(e)}", "error")

    def show(self):
        """Show the dialog and return when closed."""
        self.dialog.wait_window()
        return self.import_result
