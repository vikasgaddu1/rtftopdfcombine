"""
Pattern-based mapping dialogs for the GUI.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
import logging
from src.pattern_rules import PatternRule, create_pattern_from_files, PATTERN_TEMPLATES


class PatternQuickDialog:
    """Quick pattern assignment dialog for file mapping."""

    def __init__(self, parent, session_state, selected_files: List[str] = None):
        self.parent = parent
        self.session_state = session_state
        self.selected_files = selected_files or []
        self.result = None

        # Create top-level window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Quick Pattern Assignment")
        self.dialog.geometry("700x600")
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
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Selected files section
        if self.selected_files:
            selected_label = ttk.Label(main_frame, text=f"Selected Files ({len(self.selected_files)}):",
                                      font=("Segoe UI", 10, "bold"))
            selected_label.pack(anchor=tk.W, pady=(0, 5))

            selected_text = ttk.Label(main_frame,
                                     text=", ".join(self.selected_files[:5]) +
                                          (f"... and {len(self.selected_files) - 5} more" if len(self.selected_files) > 5 else ""),
                                     wraplength=650)
            selected_text.pack(anchor=tk.W, pady=(0, 10))

        # Pattern section
        pattern_frame = ttk.LabelFrame(main_frame, text="Pattern", padding="10")
        pattern_frame.pack(fill=tk.X, pady=(0, 10))

        # Help text
        help_label = ttk.Label(pattern_frame,
                              text="💡 Tip: Edit the pattern below to match your files (e.g., change ^f.* to ^fslb.*)",
                              font=('TkDefaultFont', 8, 'italic'),
                              foreground='#666')
        help_label.pack(anchor=tk.W, pady=(0, 5))

        # Pattern input
        pattern_input_frame = ttk.Frame(pattern_frame)
        pattern_input_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(pattern_input_frame, text="Pattern:").pack(side=tk.LEFT, padx=(0, 5))
        self.pattern_var = tk.StringVar()
        self.pattern_entry = ttk.Entry(pattern_input_frame, textvariable=self.pattern_var, width=40)
        self.pattern_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Suggest pattern button
        suggest_btn = ttk.Button(pattern_input_frame, text="Suggest", command=self._suggest_pattern)
        suggest_btn.pack(side=tk.LEFT)

        # Pattern type
        type_frame = ttk.Frame(pattern_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))

        self.is_regex = tk.BooleanVar(value=True)
        ttk.Radiobutton(type_frame, text="Regex", variable=self.is_regex,
                       value=True, command=self._update_preview).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="Wildcard", variable=self.is_regex,
                       value=False, command=self._update_preview).pack(side=tk.LEFT)

        # Test pattern button
        test_btn = ttk.Button(pattern_frame, text="Test Pattern", command=self._update_preview)
        test_btn.pack(anchor=tk.W, pady=(5, 0))

        # Pattern templates
        templates_frame = ttk.LabelFrame(main_frame, text="Pattern Templates", padding="10")
        templates_frame.pack(fill=tk.X, pady=(0, 10))

        self.template_combo = ttk.Combobox(templates_frame, state="readonly", width=60)
        self.template_combo['values'] = [t['name'] + " - " + t['example'] for t in PATTERN_TEMPLATES]
        self.template_combo.pack(fill=tk.X, pady=(0, 5))
        self.template_combo.bind('<<ComboboxSelected>>', self._apply_template)

        # Preview section
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.preview_label = ttk.Label(preview_frame, text="Enter a pattern and click 'Test Pattern' to see matches")
        self.preview_label.pack(anchor=tk.W, pady=(0, 5))

        # Preview listbox with scrollbar
        list_frame = ttk.Frame(preview_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.preview_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=10)
        self.preview_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.preview_listbox.yview)

        # Section selection
        section_frame = ttk.LabelFrame(main_frame, text="Target Section", padding="10")
        section_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(section_frame, text="Section:").pack(side=tk.LEFT, padx=(0, 5))
        self.section_var = tk.StringVar()
        self.section_combo = ttk.Combobox(section_frame, textvariable=self.section_var,
                                         state="readonly", width=50)
        self.section_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Populate sections
        sections = [f"{s.section_number} - {s.section_label}"
                   for s in self.session_state.section_definitions]
        self.section_combo['values'] = sections
        if sections:
            self.section_combo.current(0)

        # Save as rule option
        self.save_rule_var = tk.BooleanVar(value=False)
        save_check = ttk.Checkbutton(main_frame, text="Save as permanent rule",
                                    variable=self.save_rule_var)
        save_check.pack(anchor=tk.W, pady=(0, 10))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        apply_btn = ttk.Button(button_frame, text="Apply to Matched Files",
                              command=self._apply_pattern)
        apply_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT)

        # Bind pattern entry changes to preview update
        self.pattern_var.trace_add("write", lambda *args: self._update_preview())

        # Auto-suggest pattern if files selected
        if self.selected_files:
            self._suggest_pattern()

    def _suggest_pattern(self):
        """Suggest a pattern based on selected files."""
        if not self.selected_files:
            messagebox.showinfo("No Selection",
                              "Please select files in the File Mapping tab first.",
                              parent=self.dialog)
            return

        suggested = create_pattern_from_files(self.selected_files)
        if suggested:
            self.pattern_var.set(suggested)
            self._update_preview()
        else:
            messagebox.showinfo("No Pattern Found",
                              "Could not find a common pattern in the selected files.",
                              parent=self.dialog)

    def _apply_template(self, event=None):
        """Apply a pattern template."""
        selection = self.template_combo.current()
        if selection >= 0:
            template = PATTERN_TEMPLATES[selection]
            self.pattern_var.set(template['pattern'])
            self.is_regex.set(template['is_regex'])
            self._update_preview()

    def _update_preview(self):
        """Update the preview of matching files."""
        pattern = self.pattern_var.get()
        if not pattern:
            self.preview_label.config(text="Enter a pattern to see matches")
            self.preview_listbox.delete(0, tk.END)
            return

        # Validate pattern
        is_valid, error_msg = self.session_state.pattern_rule_manager.validate_pattern(
            pattern, self.is_regex.get()
        )

        if not is_valid:
            self.preview_label.config(text=f"Invalid pattern: {error_msg}")
            self.preview_listbox.delete(0, tk.END)
            return

        # Get matching files
        all_filenames = [m.filename for m in self.session_state.file_mappings if not m.ignore]
        matches = self.session_state.pattern_rule_manager.preview_matches(
            pattern, all_filenames, self.is_regex.get()
        )

        # Update UI
        self.preview_label.config(text=f"This pattern matches {len(matches)} file(s):")
        self.preview_listbox.delete(0, tk.END)

        for filename in matches[:100]:  # Limit display to 100 files
            self.preview_listbox.insert(tk.END, filename)

        if len(matches) > 100:
            self.preview_listbox.insert(tk.END, f"... and {len(matches) - 100} more")

    def _apply_pattern(self):
        """Apply the pattern to matching files."""
        pattern = self.pattern_var.get()
        section = self.section_var.get()

        if not pattern:
            messagebox.showerror("Missing Pattern", "Please enter a pattern.", parent=self.dialog)
            return

        if not section:
            messagebox.showerror("Missing Section", "Please select a section.", parent=self.dialog)
            return

        # Validate pattern
        is_valid, error_msg = self.session_state.pattern_rule_manager.validate_pattern(
            pattern, self.is_regex.get()
        )

        if not is_valid:
            messagebox.showerror("Invalid Pattern", error_msg, parent=self.dialog)
            return

        # Get section number from combo selection
        section_number = section.split(" - ")[0]

        # Get matching files
        all_filenames = [m.filename for m in self.session_state.file_mappings if not m.ignore]
        matches = self.session_state.pattern_rule_manager.preview_matches(
            pattern, all_filenames, self.is_regex.get()
        )

        if not matches:
            messagebox.showwarning("No Matches",
                                  "This pattern doesn't match any files.",
                                  parent=self.dialog)
            return

        # Confirm application
        if not messagebox.askyesno("Confirm Pattern Application",
                                  f"Apply section {section_number} to {len(matches)} file(s)?",
                                  parent=self.dialog):
            return

        # Apply pattern to mappings
        for mapping in self.session_state.file_mappings:
            if mapping.filename in matches:
                mapping.section_number = section_number

        # Save as rule if requested
        if self.save_rule_var.get():
            rule = PatternRule(
                pattern=pattern,
                section_number=section_number,
                is_regex=self.is_regex.get(),
                priority=10
            )
            self.session_state.pattern_rule_manager.add_rule(rule)
            logging.info(f"Saved pattern rule: {pattern} -> {section_number}")

        self.result = {
            'pattern': pattern,
            'section_number': section_number,
            'matches': matches,
            'saved_as_rule': self.save_rule_var.get()
        }

        self.dialog.destroy()

    def _cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()

    def show(self) -> Optional[dict]:
        """Show the dialog and return the result."""
        self.dialog.wait_window()
        return self.result


class PatternRulesDialog:
    """Dialog for managing pattern rules."""

    def __init__(self, parent, session_state):
        self.parent = parent
        self.session_state = session_state

        # Create top-level window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Pattern Rules Management")
        self.dialog.geometry("900x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_window()
        self._refresh_rules_list()

    def _center_window(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="➕ Add Rule", command=self._add_rule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="✏️ Edit", command=self._edit_rule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="🗑️ Delete", command=self._delete_rule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="⚡ Apply All Rules", command=self._apply_all_rules).pack(side=tk.LEFT, padx=(0, 5))

        # Rules list
        list_frame = ttk.LabelFrame(main_frame, text="Pattern Rules", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview for rules
        columns = ("pattern", "section", "priority", "type", "active")
        self.rules_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        self.rules_tree.heading("pattern", text="Pattern")
        self.rules_tree.heading("section", text="Section")
        self.rules_tree.heading("priority", text="Priority")
        self.rules_tree.heading("type", text="Type")
        self.rules_tree.heading("active", text="Active")

        self.rules_tree.column("pattern", width=250)
        self.rules_tree.column("section", width=150)
        self.rules_tree.column("priority", width=80)
        self.rules_tree.column("type", width=80)
        self.rules_tree.column("active", width=60)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.rules_tree.yview)
        self.rules_tree.configure(yscrollcommand=scrollbar.set)

        self.rules_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection event
        self.rules_tree.bind('<<TreeviewSelect>>', self._on_rule_select)
        self.rules_tree.bind('<Double-1>', lambda e: self._edit_rule())

        # Details frame
        details_frame = ttk.LabelFrame(main_frame, text="Rule Details", padding="10")
        details_frame.pack(fill=tk.X, pady=(0, 10))

        self.details_text = tk.Text(details_frame, height=4, state='disabled', wrap=tk.WORD)
        self.details_text.pack(fill=tk.X)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT)

    def _refresh_rules_list(self):
        """Refresh the rules list display."""
        # Clear existing items
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        # Add rules
        for rule in self.session_state.pattern_rule_manager.rules:
            section = self.session_state.get_section(rule.section_number)
            section_display = f"{rule.section_number}"
            if section:
                section_display += f" - {section.section_label[:30]}"

            self.rules_tree.insert("", tk.END, values=(
                rule.pattern,
                section_display,
                rule.priority,
                "Regex" if rule.is_regex else "Wildcard",
                "✓" if rule.is_active else "✗"
            ), tags=(rule.pattern,))

    def _on_rule_select(self, event=None):
        """Handle rule selection."""
        selection = self.rules_tree.selection()
        if not selection:
            return

        # Get selected rule
        item = self.rules_tree.item(selection[0])
        pattern = item['values'][0]

        # Find rule
        rule = None
        for r in self.session_state.pattern_rule_manager.rules:
            if r.pattern == pattern:
                rule = r
                break

        if rule:
            # Show details
            self.details_text.configure(state='normal')
            self.details_text.delete(1.0, tk.END)

            details = f"Pattern: {rule.pattern}\n"
            details += f"Section: {rule.section_number}\n"
            details += f"Priority: {rule.priority}\n"
            details += f"Description: {rule.description or '(none)'}\n"

            # Get match count
            all_filenames = [m.filename for m in self.session_state.file_mappings if not m.ignore]
            matches = self.session_state.pattern_rule_manager.preview_matches(
                rule.pattern, all_filenames, rule.is_regex
            )
            details += f"Matches: {len(matches)} file(s)"

            self.details_text.insert(1.0, details)
            self.details_text.configure(state='disabled')

    def _add_rule(self):
        """Add a new rule."""
        dialog = PatternRuleEditDialog(self.dialog, self.session_state)
        if dialog.show():
            self._refresh_rules_list()

    def _edit_rule(self):
        """Edit the selected rule."""
        selection = self.rules_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a rule to edit.", parent=self.dialog)
            return

        item = self.rules_tree.item(selection[0])
        pattern = item['values'][0]

        # Find rule
        rule_index = None
        for i, r in enumerate(self.session_state.pattern_rule_manager.rules):
            if r.pattern == pattern:
                rule_index = i
                break

        if rule_index is not None:
            rule = self.session_state.pattern_rule_manager.rules[rule_index]
            dialog = PatternRuleEditDialog(self.dialog, self.session_state, rule)
            if dialog.show():
                self._refresh_rules_list()

    def _delete_rule(self):
        """Delete the selected rule."""
        selection = self.rules_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a rule to delete.", parent=self.dialog)
            return

        if not messagebox.askyesno("Confirm Delete", "Delete the selected rule?", parent=self.dialog):
            return

        item = self.rules_tree.item(selection[0])
        pattern = item['values'][0]

        self.session_state.pattern_rule_manager.remove_rule(pattern)
        self._refresh_rules_list()
        logging.info(f"Deleted pattern rule: {pattern}")

    def _apply_all_rules(self):
        """Apply all active rules to file mappings."""
        if not self.session_state.pattern_rule_manager.rules:
            messagebox.showinfo("No Rules", "No pattern rules defined.", parent=self.dialog)
            return

        # Ask if should override existing mappings
        override = messagebox.askyesnocancel(
            "Apply Rules",
            "Override existing section assignments?\n\nYes = Override all\nNo = Only unmapped files\nCancel = Don't apply",
            parent=self.dialog
        )

        if override is None:
            return

        # Apply rules
        stats = self.session_state.pattern_rule_manager.apply_rules_to_mappings(
            self.session_state.file_mappings,
            override_existing=override
        )

        messagebox.showinfo(
            "Rules Applied",
            f"Pattern rules applied:\n"
            f"  • Applied: {stats['applied']} files\n"
            f"  • Skipped: {stats['skipped']} files\n"
            f"  • Failed: {stats['failed']} files",
            parent=self.dialog
        )

    def show(self):
        """Show the dialog."""
        self.dialog.wait_window()


class PatternRuleEditDialog:
    """Dialog for editing a single pattern rule."""

    def __init__(self, parent, session_state, rule: Optional[PatternRule] = None):
        self.parent = parent
        self.session_state = session_state
        self.rule = rule  # None for new rule, PatternRule for editing
        self.result = False

        # Create top-level window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Pattern Rule" if rule else "Add Pattern Rule")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_window()

        # Load rule data if editing
        if self.rule:
            self._load_rule_data()

    def _center_window(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Pattern
        ttk.Label(main_frame, text="Pattern:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.pattern_var = tk.StringVar()
        self.pattern_entry = ttk.Entry(main_frame, textvariable=self.pattern_var)
        self.pattern_entry.pack(fill=tk.X, pady=(0, 10))

        # Pattern type
        type_frame = ttk.Frame(main_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(type_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 10))
        self.is_regex = tk.BooleanVar(value=True)
        ttk.Radiobutton(type_frame, text="Regex", variable=self.is_regex, value=True).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="Wildcard", variable=self.is_regex, value=False).pack(side=tk.LEFT)

        # Section
        ttk.Label(main_frame, text="Section:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.section_var = tk.StringVar()
        self.section_combo = ttk.Combobox(main_frame, textvariable=self.section_var, state="readonly")
        self.section_combo.pack(fill=tk.X, pady=(0, 10))

        # Populate sections
        sections = [f"{s.section_number} - {s.section_label}"
                   for s in self.session_state.section_definitions]
        self.section_combo['values'] = sections
        if sections:
            self.section_combo.current(0)

        # Priority
        priority_frame = ttk.Frame(main_frame)
        priority_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(priority_frame, text="Priority:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        self.priority_var = tk.IntVar(value=10)
        priority_spinbox = ttk.Spinbox(priority_frame, from_=0, to=100, textvariable=self.priority_var, width=10)
        priority_spinbox.pack(side=tk.LEFT)
        ttk.Label(priority_frame, text="(Higher = override lower priority)").pack(side=tk.LEFT, padx=(10, 0))

        # Description
        ttk.Label(main_frame, text="Description (optional):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.description_var = tk.StringVar()
        description_entry = ttk.Entry(main_frame, textvariable=self.description_var)
        description_entry.pack(fill=tk.X, pady=(0, 10))

        # Active checkbox
        self.active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Active", variable=self.active_var).pack(anchor=tk.W, pady=(0, 10))

        # Preview button
        ttk.Button(main_frame, text="Test Pattern", command=self._test_pattern).pack(anchor=tk.W, pady=(0, 10))

        # Preview listbox
        preview_frame = ttk.LabelFrame(main_frame, text="Preview Matches", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.preview_listbox = tk.Listbox(preview_frame, height=8)
        self.preview_listbox.pack(fill=tk.BOTH, expand=True)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)

    def _load_rule_data(self):
        """Load data from the rule being edited."""
        self.pattern_var.set(self.rule.pattern)
        self.is_regex.set(self.rule.is_regex)
        self.priority_var.set(self.rule.priority)
        self.description_var.set(self.rule.description)
        self.active_var.set(self.rule.is_active)

        # Set section
        for i, section in enumerate(self.session_state.section_definitions):
            if section.section_number == self.rule.section_number:
                self.section_combo.current(i)
                break

    def _test_pattern(self):
        """Test the pattern and show preview."""
        pattern = self.pattern_var.get()
        if not pattern:
            messagebox.showwarning("Missing Pattern", "Please enter a pattern.", parent=self.dialog)
            return

        # Validate pattern
        is_valid, error_msg = self.session_state.pattern_rule_manager.validate_pattern(
            pattern, self.is_regex.get()
        )

        if not is_valid:
            messagebox.showerror("Invalid Pattern", error_msg, parent=self.dialog)
            return

        # Get matching files
        all_filenames = [m.filename for m in self.session_state.file_mappings if not m.ignore]
        matches = self.session_state.pattern_rule_manager.preview_matches(
            pattern, all_filenames, self.is_regex.get()
        )

        # Update preview
        self.preview_listbox.delete(0, tk.END)
        self.preview_listbox.insert(0, f"Matches {len(matches)} file(s):")

        for filename in matches[:50]:  # Limit display to 50 files
            self.preview_listbox.insert(tk.END, f"  {filename}")

        if len(matches) > 50:
            self.preview_listbox.insert(tk.END, f"  ... and {len(matches) - 50} more")

    def _save(self):
        """Save the rule."""
        pattern = self.pattern_var.get()
        section = self.section_var.get()

        if not pattern:
            messagebox.showerror("Missing Pattern", "Please enter a pattern.", parent=self.dialog)
            return

        if not section:
            messagebox.showerror("Missing Section", "Please select a section.", parent=self.dialog)
            return

        # Validate pattern
        is_valid, error_msg = self.session_state.pattern_rule_manager.validate_pattern(
            pattern, self.is_regex.get()
        )

        if not is_valid:
            messagebox.showerror("Invalid Pattern", error_msg, parent=self.dialog)
            return

        # Get section number
        section_number = section.split(" - ")[0]

        # Create or update rule
        new_rule = PatternRule(
            pattern=pattern,
            section_number=section_number,
            description=self.description_var.get(),
            priority=self.priority_var.get(),
            is_regex=self.is_regex.get(),
            is_active=self.active_var.get()
        )

        if self.rule:
            # Update existing rule
            self.session_state.pattern_rule_manager.update_rule(self.rule.pattern, new_rule)
            logging.info(f"Updated pattern rule: {pattern}")
        else:
            # Add new rule
            if not self.session_state.pattern_rule_manager.add_rule(new_rule):
                messagebox.showerror("Duplicate Pattern",
                                   "A rule with this pattern already exists.",
                                   parent=self.dialog)
                return
            logging.info(f"Added pattern rule: {pattern}")

        self.result = True
        self.dialog.destroy()

    def _cancel(self):
        """Cancel the dialog."""
        self.dialog.destroy()

    def show(self) -> bool:
        """Show the dialog and return True if saved."""
        self.dialog.wait_window()
        return self.result
