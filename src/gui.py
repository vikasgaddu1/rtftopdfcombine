import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from pathlib import Path
import threading
import queue
import sys
import os
import gc

# Import the GUI configuration and session state
from src.gui_config import GUIConfig
from src.session_state import SessionState, load_default_ich_sections

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.update_timer = None

    def write(self, string):
        self.queue.put(string)
        if self.update_timer is None:
            self.update_timer = self.text_widget.after(100, self.update_text)

    def update_text(self):
        while not self.queue.empty():
            string = self.queue.get()
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.update_timer = None

    def flush(self):
        pass

class RTF2PDFGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RTF to PDF Converter with TOC")
        self.root.geometry("900x700")

        # Add maximize button functionality
        self.root.state('normal')  # Ensure window is normal state

        # Set theme colors
        self.bg_color = "#f0f0f0"
        self.accent_color = "#007bff"
        self.success_color = "#28a745"
        self.warning_color = "#ffc107"
        self.danger_color = "#dc3545"
        self.root.configure(bg=self.bg_color)

        # Configure ttk styles
        self.setup_styles()

        # Initialize session state
        self.session_state = SessionState()

        # Create main notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create Main tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main")

        # Create Configuration tab
        self.config_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.config_tab, text="Configuration")

        # Variables for main tab
        self.input_folder = tk.StringVar(value=str(Path.cwd() / "input"))
        self.output_folder = tk.StringVar(value=str(Path.cwd() / "output"))
        self.output_filename = tk.StringVar(value="final_document_with_toc.pdf")

        # Sort mode variable
        self.sort_mode = tk.StringVar(value="default")

        # PDF settings
        self.page_width = tk.StringVar(value="210")
        self.margin = tk.StringVar(value="15")
        self.font_size = tk.StringVar(value="8")
        self.header_font_size = tk.StringVar(value="10")
        self.parallel_workers = tk.IntVar(value=3)

        # Processing control variables
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.is_processing = False

        # Build Main tab
        self.create_main_tab()

        # Build Configuration tab
        self.create_config_tab()

        # Add menu bar with maximize option
        self.create_menu_bar()

        # Cleanup when window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Bind input folder change
        self.input_folder.trace('w', self.on_input_folder_change)

        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()

    def setup_styles(self):
        """Configure ttk styles for better visual appearance."""
        style = ttk.Style()

        # Configure button styles
        style.configure('Process.TButton',
                       foreground='black',
                       background=self.success_color,
                       font=('TkDefaultFont', 11, 'bold'),
                       padding=15)

        style.configure('Accent.TButton',
                       foreground='white',
                       background=self.accent_color,
                       font=('TkDefaultFont', 10, 'bold'),
                       padding=10)

        style.configure('Success.TButton',
                       foreground='white',
                       background=self.success_color,
                       font=('TkDefaultFont', 10),
                       padding=8)

        style.configure('Stop.TButton',
                       foreground='black',
                       background=self.danger_color,
                       font=('TkDefaultFont', 10, 'bold'),
                       padding=10)

        # Configure frame styles
        style.configure('Card.TFrame', relief='solid', borderwidth=1)

        # Configure label styles
        style.configure('Title.TLabel', font=('TkDefaultFont', 12, 'bold'))
        style.configure('Subtitle.TLabel', font=('TkDefaultFont', 10))
        style.configure('Info.TLabel', font=('TkDefaultFont', 9, 'italic'), foreground='#666')

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions."""
        # Global shortcuts
        self.root.bind('<Control-o>', lambda e: self.browse_input())
        self.root.bind('<Control-s>', lambda e: self.export_config())
        self.root.bind('<Control-i>', lambda e: self.import_config())
        self.root.bind('<F5>', lambda e: self.start_processing())
        self.root.bind('<Escape>', lambda e: self.stop_processing())
        self.root.bind('<F1>', lambda e: self.show_help())
        self.root.bind('<F11>', lambda e: self.maximize_window())

    def show_help(self):
        """Show help dialog with keyboard shortcuts."""
        help_text = """
RTF to PDF Converter - Keyboard Shortcuts

Global Shortcuts:
  Ctrl+O        - Browse Input Folder
  Ctrl+I        - Import Configuration
  Ctrl+S        - Export Configuration
  F5            - Start Processing
  Escape        - Stop Processing
  F1            - Show this help
  F11           - Maximize Window

Sort Modes:
  Default Sort  - Automatic alphabetical sorting
  ICH Sort      - Use ICH E3 section structure
  Custom Sort   - Define your own sections

Configuration Tab:
  Double-click  - Edit section or file mapping
  Single-click  - Toggle ignore checkbox (File Mapping)
  Enter         - Save dialog
  Escape        - Cancel dialog
"""
        messagebox.showinfo("Help - Keyboard Shortcuts", help_text)

    def create_menu_bar(self):
        """Create menu bar with window controls."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Browse Input Folder", command=self.browse_input, accelerator="Ctrl+O")
        file_menu.add_command(label="Import Config", command=self.import_config, accelerator="Ctrl+I")
        file_menu.add_command(label="Export Config", command=self.export_config, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Window menu
        window_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Window", menu=window_menu)
        window_menu.add_command(label="Maximize", command=self.maximize_window, accelerator="F11")
        window_menu.add_command(label="Restore", command=self.restore_window)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_help, accelerator="F1")
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)

    def show_about(self):
        """Show about dialog."""
        about_text = """RTF to PDF Converter with TOC

Version: 2.0
Integrated Sort Feature

Features:
• Convert RTF files to PDF
• Three sort modes: Default, ICH, Custom
• Interactive section management
• File mapping with drag-drop support
• Configuration export/import
• Real-time validation

© 2024 - Built with Python & Tkinter"""
        messagebox.showinfo("About", about_text)

    def maximize_window(self):
        """Maximize the application window."""
        self.root.state('zoomed')

    def restore_window(self):
        """Restore window to normal size."""
        self.root.state('normal')

    def create_main_tab(self):
        """Create the main processing tab."""
        # Create scrollable frame for main tab
        main_frame = ttk.Frame(self.main_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input/Output Settings
        input_frame = ttk.LabelFrame(main_frame, text="Input/Output Settings", padding="5")
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="Input Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.input_folder, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(input_frame, text="Output Folder:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.output_folder, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(input_frame, text="Output Filename:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.output_filename, width=50).grid(row=2, column=1, padx=5, pady=5)

        # Sort Mode Selection
        sort_frame = ttk.LabelFrame(main_frame, text="Sort Mode", padding="5")
        sort_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(sort_frame, text="Default Sort (Alphabetical)",
                       variable=self.sort_mode, value="default",
                       command=self.on_sort_mode_change).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(sort_frame, text="ICH Sort (ICH E3 Sections)",
                       variable=self.sort_mode, value="ich",
                       command=self.on_sort_mode_change).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(sort_frame, text="Custom Sort (Define Your Own)",
                       variable=self.sort_mode, value="custom",
                       command=self.on_sort_mode_change).pack(anchor=tk.W, pady=2)

        # PDF Options
        pdf_frame = ttk.LabelFrame(main_frame, text="PDF Options", padding="5")
        pdf_frame.pack(fill=tk.X, pady=5)

        ttk.Label(pdf_frame, text="Page Width (mm):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(pdf_frame, textvariable=self.page_width, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(pdf_frame, text="Margin (mm):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(pdf_frame, textvariable=self.margin, width=10).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)

        ttk.Label(pdf_frame, text="Font Size:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(pdf_frame, textvariable=self.font_size, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(pdf_frame, text="Header Font Size:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(pdf_frame, textvariable=self.header_font_size, width=10).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)

        ttk.Label(pdf_frame, text="Parallel Workers:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        worker_spinbox = ttk.Spinbox(pdf_frame, from_=1, to=10, textvariable=self.parallel_workers, width=10)
        worker_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(pdf_frame, text="(Number of RTF files to convert simultaneously)",
                 font=('TkDefaultFont', 8, 'italic')).grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=5)

        # Process buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        self.process_btn = ttk.Button(
            button_frame,
            text="▶ Process Files",
            command=self.start_processing,
            style='Process.TButton'
        )
        self.process_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹ Stop",
            command=self.stop_processing,
            state='disabled',
            style='Stop.TButton'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=10)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, pady=5)

        # Log display
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.configure(state='disabled')

        # Scrollbar for log
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # Set up logging
        self.setup_logging()

        # Create custom styles
        style = ttk.Style()
        style.configure('Accent.TButton', background=self.accent_color)
        style.configure('Stop.TButton', background='#dc3545')

    def create_config_tab(self):
        """Create the configuration tab with sub-tabs."""
        # Configuration buttons at the top (shown only for ICH/Custom modes)
        self.config_buttons_frame = ttk.Frame(self.config_tab)
        self.config_buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(self.config_buttons_frame, text="Configuration:",
                 font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.config_buttons_frame, text="📥 Import Config",
                  command=self.import_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.config_buttons_frame, text="📤 Export Config",
                  command=self.export_config).pack(side=tk.LEFT, padx=5)

        # Hide config buttons initially (default mode is selected)
        self.config_buttons_frame.pack_forget()

        # Create notebook for configuration sub-tabs
        self.config_notebook = ttk.Notebook(self.config_tab)
        self.config_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create File Mapping tab
        self.file_mapping_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(self.file_mapping_frame, text="File Mapping")

        # Create Section Definition tab
        self.section_def_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(self.section_def_frame, text="Section Definition")

        # Build File Mapping tab
        self.create_file_mapping_tab()

        # Build Section Definition tab
        self.create_section_definition_tab()

        # Initially hide configuration tab if in default mode
        self.update_config_tab_visibility()

    def create_file_mapping_tab(self):
        """Create the file mapping interface."""
        # Instructions
        instructions = ttk.Label(
            self.file_mapping_frame,
            text="💡 Double-click Section to assign | Click Ignore checkbox to toggle",
            font=('TkDefaultFont', 9, 'italic'),
            foreground='#666'
        )
        instructions.pack(fill=tk.X, padx=10, pady=(5, 0))

        # Table frame with scrollbars
        table_frame = ttk.Frame(self.file_mapping_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create Treeview for file mappings
        columns = ("filename", "section", "ignore", "status")
        self.files_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        self.files_tree.heading("filename", text="File Name")
        self.files_tree.heading("section", text="Section Number")
        self.files_tree.heading("ignore", text="Ignore?")
        self.files_tree.heading("status", text="Status")

        self.files_tree.column("filename", width=200)
        self.files_tree.column("section", width=300)
        self.files_tree.column("ignore", width=80, anchor='center')
        self.files_tree.column("status", width=120)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.files_tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.files_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Bind events
        self.files_tree.bind("<Double-1>", self.on_file_double_click)
        self.files_tree.bind("<Button-1>", self.on_file_single_click)

        # Summary frame
        self.files_summary_frame = ttk.Frame(self.file_mapping_frame)
        self.files_summary_frame.pack(fill=tk.X, padx=10, pady=5)

        self.files_summary_label = ttk.Label(
            self.files_summary_frame,
            text="Files: 0 | Mapped: 0 | Ignored: 0 | Unmapped: 0"
        )
        self.files_summary_label.pack(anchor=tk.W)

    def on_file_single_click(self, event):
        """Handle single click on file mapping table."""
        region = self.files_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.files_tree.identify_column(event.x)
            item = self.files_tree.identify_row(event.y)

            if not item:
                return

            # If clicked on Ignore column, toggle it
            if column == "#3":  # Ignore column
                self.toggle_file_ignore(item)

    def on_file_double_click(self, event):
        """Handle double-click on file mapping table."""
        region = self.files_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.files_tree.identify_column(event.x)
            item = self.files_tree.identify_row(event.y)

            if not item:
                return

            # If double-clicked on Section column, show dropdown
            if column == "#2":  # Section column
                self.edit_file_section(item, event.x, event.y)

    def toggle_file_ignore(self, item):
        """Toggle the ignore status for a file."""
        values = self.files_tree.item(item, "values")
        filename = values[0]

        # Get the mapping and toggle ignore
        mapping = self.session_state.get_mapping(filename)
        if mapping:
            mapping.ignore = not mapping.ignore
            logging.info(f"File '{filename}' ignore status: {mapping.ignore}")
            self.refresh_file_mapping_row(item, mapping)
            self.update_files_summary()

    def edit_file_section(self, item, x, y):
        """Show dropdown to edit file section."""
        # Get item position
        bbox = self.files_tree.bbox(item, column="#2")
        if not bbox:
            return

        values = self.files_tree.item(item, "values")
        filename = values[0]
        current_section = values[1]

        # Get the mapping
        mapping = self.session_state.get_mapping(filename)
        if not mapping or mapping.ignore:
            return  # Don't allow editing ignored files

        # Create combobox for section selection
        section_values = []
        for section in self.session_state.section_definitions:
            section_values.append(f"{section.section_number} - {section.section_label}")

        # Create popup combobox with search capability
        combo = ttk.Combobox(
            self.files_tree,
            values=section_values,
            font=('TkDefaultFont', 10),
            width=50
        )

        # Set current value
        if current_section and current_section != "Not Mapped":
            combo.set(current_section)
        else:
            combo.set("")

        # Store all values for filtering
        all_values = section_values.copy()

        # Position the combobox (make it wider than the column for better visibility)
        combo.place(x=bbox[0], y=bbox[1], width=min(450, bbox[2] + 150), height=bbox[3])
        combo.focus()

        # Automatically show the dropdown
        combo.event_generate('<Button-1>')

        def on_keyrelease(event):
            """Filter dropdown as user types."""
            typed = combo.get().lower()
            if typed == "":
                combo['values'] = all_values
            else:
                # Filter values based on typed text
                filtered = [v for v in all_values if typed in v.lower()]
                combo['values'] = filtered

            # Keep dropdown open and show filtered results
            if filtered:
                combo.event_generate('<Down>')

        def on_select(event):
            selected = combo.get()
            if selected and selected in all_values:
                # Extract section number
                section_number = selected.split(" - ")[0]
                mapping.section_number = section_number
                logging.info(f"Mapped file '{filename}' to section '{section_number}'")
                self.refresh_file_mapping_row(item, mapping)
                self.update_files_summary()
                self.update_sections_summary()  # Update section stats
            combo.destroy()

        def on_focusout(event):
            combo.destroy()

        combo.bind("<KeyRelease>", on_keyrelease)
        combo.bind("<<ComboboxSelected>>", on_select)
        combo.bind("<FocusOut>", on_focusout)
        combo.bind("<Escape>", lambda e: combo.destroy())
        combo.bind("<Return>", on_select)

    def refresh_file_mapping_row(self, item, mapping):
        """Refresh a single row in the file mapping table."""
        # Get section label
        section_display = "Not Mapped"
        if mapping.section_number:
            section = self.session_state.get_section(mapping.section_number)
            if section:
                section_display = f"{section.section_number} - {section.section_label}"

        # Get status with emoji
        status_text = {
            "mapped": "✅ Mapped",
            "unmapped": "⚠️ Not Mapped",
            "ignored": "🚫 Ignored"
        }.get(mapping.status, mapping.status)

        # Get ignore display
        ignore_display = "✓" if mapping.ignore else ""

        # Update row
        self.files_tree.item(item, values=(
            mapping.filename,
            section_display,
            ignore_display,
            status_text
        ))

        # Apply row styling
        if mapping.ignore:
            self.files_tree.item(item, tags=("ignored",))
        else:
            self.files_tree.item(item, tags=())

        # Configure tag colors
        self.files_tree.tag_configure("ignored", foreground="gray")

    def refresh_file_mapping_display(self):
        """Refresh the entire file mapping table."""
        # Clear existing items
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)

        # Add files from session state
        for mapping in self.session_state.file_mappings:
            # Get section label
            section_display = "Not Mapped"
            if mapping.section_number:
                section = self.session_state.get_section(mapping.section_number)
                if section:
                    section_display = f"{section.section_number} - {section.section_label}"

            # Get status
            status_text = {
                "mapped": "✅ Mapped",
                "unmapped": "⚠️ Not Mapped",
                "ignored": "🚫 Ignored"
            }.get(mapping.status, mapping.status)

            # Get ignore display with clearer checkbox symbols
            ignore_display = "☑" if mapping.ignore else "☐"

            # Insert row
            item = self.files_tree.insert("", tk.END, values=(
                mapping.filename,
                section_display,
                ignore_display,
                status_text
            ))

            # Apply styling
            if mapping.ignore:
                self.files_tree.item(item, tags=("ignored",))

        # Configure tag colors
        self.files_tree.tag_configure("ignored", foreground="gray")

        # Update summary
        self.update_files_summary()

    def update_files_summary(self):
        """Update the files summary label."""
        stats = self.session_state.get_statistics()
        summary_text = (
            f"Files: {stats['total_files']} | "
            f"Mapped: {stats['mapped_files']} | "
            f"Ignored: {stats['ignored_files']} | "
            f"Unmapped: {stats['unmapped_files']}"
        )
        self.files_summary_label.config(text=summary_text)

    def update_file_mapping_display(self):
        """Update the file mapping display (called from other tabs)."""
        self.refresh_file_mapping_display()

    def create_section_definition_tab(self):
        """Create the section definition interface."""
        # Button frame at top
        button_frame = ttk.Frame(self.section_def_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="Add Section",
                  command=self.add_section).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Selected",
                  command=self.edit_section).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected",
                  command=self.delete_section).pack(side=tk.LEFT, padx=5)

        # Reset button (only for ICH mode)
        self.reset_sections_btn = ttk.Button(button_frame, text="Reset to ICH Defaults",
                                             command=self.reset_ich_sections)
        self.reset_sections_btn.pack(side=tk.LEFT, padx=5)

        # Table frame with scrollbars
        table_frame = ttk.Frame(self.section_def_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create Treeview for sections
        columns = ("section_number", "section_label")
        self.sections_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        self.sections_tree.heading("section_number", text="Section Number")
        self.sections_tree.heading("section_label", text="Section Label")

        self.sections_tree.column("section_number", width=150)
        self.sections_tree.column("section_label", width=500)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.sections_tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.sections_tree.xview)
        self.sections_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.sections_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Double-click to edit
        self.sections_tree.bind("<Double-1>", lambda e: self.edit_section())

        # Summary frame
        self.sections_summary_frame = ttk.Frame(self.section_def_frame)
        self.sections_summary_frame.pack(fill=tk.X, padx=10, pady=5)

        self.sections_summary_label = ttk.Label(
            self.sections_summary_frame,
            text="Sections: 0 | Used: 0 | Unused: 0"
        )
        self.sections_summary_label.pack(anchor=tk.W)

    def refresh_sections_display(self):
        """Refresh the sections tree view."""
        # Clear existing items
        for item in self.sections_tree.get_children():
            self.sections_tree.delete(item)

        # Add sections from session state
        for section in self.session_state.section_definitions:
            self.sections_tree.insert("", tk.END, values=(
                section.section_number,
                section.section_label
            ))

        # Update summary
        self.update_sections_summary()

        # Update reset button visibility
        if self.sort_mode.get() == "ich":
            self.reset_sections_btn.pack(side=tk.LEFT, padx=5)
        else:
            self.reset_sections_btn.pack_forget()

    def update_sections_summary(self):
        """Update the sections summary label."""
        stats = self.session_state.get_statistics()
        summary_text = (
            f"Sections: {stats['total_sections']} | "
            f"Used: {stats['used_sections']} | "
            f"Unused: {stats['total_sections'] - stats['used_sections']}"
        )
        self.sections_summary_label.config(text=summary_text)

    def add_section(self):
        """Show dialog to add a new section."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Section")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()

        # Section number
        ttk.Label(dialog, text="Section Number:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        section_number_var = tk.StringVar()
        section_number_entry = ttk.Entry(dialog, textvariable=section_number_var, width=30)
        section_number_entry.grid(row=0, column=1, padx=10, pady=10)
        section_number_entry.focus()

        # Section label
        ttk.Label(dialog, text="Section Label:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        section_label_var = tk.StringVar()
        section_label_entry = ttk.Entry(dialog, textvariable=section_label_var, width=30)
        section_label_entry.grid(row=1, column=1, padx=10, pady=10)

        def save_section():
            section_number = section_number_var.get().strip()
            section_label = section_label_var.get().strip()

            if not section_number or not section_label:
                messagebox.showerror("Error", "Both fields are required", parent=dialog)
                return

            # Try to add section
            if self.session_state.add_section(section_number, section_label):
                logging.info(f"Added section: {section_number} - {section_label}")
                self.refresh_sections_display()
                self.update_file_mapping_display()  # Update dropdowns
                dialog.destroy()
            else:
                messagebox.showerror("Error",
                                   f"Section number '{section_number}' already exists",
                                   parent=dialog)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="OK", command=save_section).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Bind Enter key
        dialog.bind("<Return>", lambda e: save_section())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def edit_section(self):
        """Edit the selected section."""
        selection = self.sections_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a section to edit")
            return

        # Get selected section details
        item = selection[0]
        values = self.sections_tree.item(item, "values")
        old_number, old_label = values

        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Section")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()

        # Section number
        ttk.Label(dialog, text="Section Number:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        section_number_var = tk.StringVar(value=old_number)
        section_number_entry = ttk.Entry(dialog, textvariable=section_number_var, width=30)
        section_number_entry.grid(row=0, column=1, padx=10, pady=10)
        section_number_entry.focus()

        # Section label
        ttk.Label(dialog, text="Section Label:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        section_label_var = tk.StringVar(value=old_label)
        section_label_entry = ttk.Entry(dialog, textvariable=section_label_var, width=30)
        section_label_entry.grid(row=1, column=1, padx=10, pady=10)

        def save_changes():
            new_number = section_number_var.get().strip()
            new_label = section_label_var.get().strip()

            if not new_number or not new_label:
                messagebox.showerror("Error", "Both fields are required", parent=dialog)
                return

            # Try to update section
            if self.session_state.update_section(old_number, new_number, new_label):
                logging.info(f"Updated section: {old_number} -> {new_number} - {new_label}")
                self.refresh_sections_display()
                self.update_file_mapping_display()  # Update dropdowns
                dialog.destroy()
            else:
                messagebox.showerror("Error",
                                   f"Section number '{new_number}' already exists",
                                   parent=dialog)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="OK", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Bind keys
        dialog.bind("<Return>", lambda e: save_changes())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def delete_section(self):
        """Delete the selected section."""
        selection = self.sections_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a section to delete")
            return

        # Get selected section details
        item = selection[0]
        values = self.sections_tree.item(item, "values")
        section_number = values[0]

        # Check if section is in use
        affected_files = []
        for mapping in self.session_state.file_mappings:
            if mapping.section_number == section_number:
                affected_files.append(mapping.filename)

        # Confirm deletion
        message = f"Are you sure you want to delete section '{section_number}'?"
        if affected_files:
            message += f"\n\nThis will unmap {len(affected_files)} file(s):"
            message += "\n" + ", ".join(affected_files[:5])
            if len(affected_files) > 5:
                message += f"\n... and {len(affected_files) - 5} more"

        if messagebox.askyesno("Confirm Delete", message):
            affected = self.session_state.delete_section(section_number)
            logging.info(f"Deleted section: {section_number} (affected {len(affected)} files)")
            self.refresh_sections_display()
            self.update_file_mapping_display()  # Update dropdowns and clear mappings

    def reset_ich_sections(self):
        """Reset sections to ICH defaults."""
        if messagebox.askyesno("Reset Sections",
                              "This will reset all sections to ICH E3 defaults.\n"
                              "Any custom sections and file mappings will be cleared.\n\n"
                              "Continue?"):
            self.load_ich_sections()
            # Clear all file mappings
            for mapping in self.session_state.file_mappings:
                mapping.section_number = None
                mapping.ignore = False
            self.refresh_sections_display()
            self.update_file_mapping_display()
            logging.info("Reset sections to ICH defaults")

    def on_sort_mode_change(self):
        """Handle sort mode selection change."""
        mode = self.sort_mode.get()

        # Reset everything when changing modes
        self.reset_ui_state()

        self.session_state.set_sort_mode(mode)

        # Show/hide configuration buttons and tab
        if mode in ["ich", "custom"]:
            self.config_buttons_frame.pack(fill=tk.X, pady=5)

            # Load ICH sections if ICH mode selected
            if mode == "ich":
                self.load_ich_sections()
            else:
                # Custom mode - clear sections for user to define
                self.session_state.section_definitions.clear()
                self.refresh_sections_display()

            # Scan RTF files for both ICH and Custom modes
            self.scan_rtf_files()
        else:
            self.config_buttons_frame.pack_forget()
            # Default mode - clear session state
            self.session_state.clear()

        # Update configuration tab visibility
        self.update_config_tab_visibility()

        logging.info(f"Sort mode changed to: {mode}")

    def reset_ui_state(self):
        """Reset UI state when changing sort modes."""
        # Reset progress bar
        self.progress_var.set(0)

        # Reset status
        self.status_var.set("Ready")

        # Clear log output
        self.log_output.configure(state='normal')
        self.log_output.delete(1.0, tk.END)
        self.log_output.configure(state='disabled')

    def update_config_tab_visibility(self):
        """Show/hide configuration tab based on sort mode."""
        mode = self.sort_mode.get()

        if mode in ["ich", "custom"]:
            # Enable Configuration tab
            self.notebook.tab(1, state="normal")
        else:
            # Disable Configuration tab and switch to Main if on Config
            if self.notebook.index("current") == 1:
                self.notebook.select(0)  # Switch to Main tab
            self.notebook.tab(1, state="disabled")

    def load_ich_sections(self):
        """Load default ICH sections into session state."""
        sections = load_default_ich_sections()
        self.session_state.section_definitions = sections
        logging.info(f"Loaded {len(sections)} ICH sections")
        self.refresh_sections_display()

    def on_input_folder_change(self, *args):
        """Handle input folder change."""
        if self.sort_mode.get() in ["ich", "custom"]:
            self.scan_rtf_files()

    def scan_rtf_files(self):
        """Scan input folder for RTF files and update session state."""
        input_path = Path(self.input_folder.get())

        if input_path.exists():
            rtf_files = list(input_path.glob("*.rtf"))
            logging.info(f"Found {len(rtf_files)} RTF files in input folder")

            self.session_state.update_rtf_files(rtf_files)

            # Update file mapping tab display
            self.refresh_file_mapping_display()

    def update_file_mapping_display(self):
        """Update the file mapping display (legacy method - calls refresh)."""
        self.refresh_file_mapping_display()

    def import_config(self):
        """Import configuration from JSON file."""
        file_path = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=Path.cwd() / "config"
        )

        if file_path:
            try:
                summary = self.session_state.import_from_json(Path(file_path))

                # Show import summary
                message = f"Configuration Imported\n\n"
                message += f"Sections loaded: {summary['sections_loaded']}\n"
                message += f"Files matched: {summary['files_matched']}\n"

                if summary['files_not_in_config'] > 0:
                    message += f"Files not in config: {summary['files_not_in_config']} (unmapped)\n"

                if summary['files_in_config_but_missing'] > 0:
                    message += f"Files in config but missing: {summary['files_in_config_but_missing']}\n"

                message += "\nReview the Configuration tab to verify mappings."

                messagebox.showinfo("Import Successful", message)
                logging.info(f"Configuration imported from: {file_path}")

                # Update all displays
                self.refresh_sections_display()
                self.refresh_file_mapping_display()
                self.update_sections_summary()
                self.update_files_summary()

            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import configuration:\n{str(e)}")
                logging.error(f"Failed to import configuration: {e}")

    def export_config(self):
        """Export current configuration to JSON file."""
        from datetime import datetime

        # Ensure config directory exists
        config_dir = Path.cwd() / "config"
        config_dir.mkdir(exist_ok=True)

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"rtf2pdf_config_{timestamp}.json"

        file_path = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=default_filename,
            initialdir=config_dir
        )

        if file_path:
            try:
                # Get project name from output filename
                project_name = self.output_filename.get().replace(".pdf", "")

                self.session_state.export_to_json(Path(file_path), project_name)
                messagebox.showinfo("Export Successful", f"Configuration exported to:\n{file_path}")
                logging.info(f"Configuration exported to: {file_path}")

            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export configuration:\n{str(e)}")
                logging.error(f"Failed to export configuration: {e}")

    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

        # Redirect logging to the text widget
        self.log_handler = RedirectText(self.log_text)
        logging.getLogger().addHandler(logging.StreamHandler(self.log_handler))

    def browse_input(self):
        """Browse for input folder."""
        folder = filedialog.askdirectory(initialdir=self.input_folder.get())
        if folder:
            self.input_folder.set(folder)

    def browse_output(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(initialdir=self.output_folder.get())
        if folder:
            self.output_folder.set(folder)

    def validate_inputs(self):
        """Validate user inputs before processing."""
        # Check input folder
        input_path = Path(self.input_folder.get())
        if not input_path.exists():
            messagebox.showerror("Error", "Input folder does not exist")
            return False

        # Check output folder
        output_path = Path(self.output_folder.get())
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output folder: {e}")
                return False

        # Validate sort mode configuration
        if self.sort_mode.get() in ["ich", "custom"]:
            is_valid, errors = self.session_state.validate_for_processing()
            if not is_valid:
                error_msg = "Validation Errors:\n\n" + "\n".join(errors)
                error_msg += "\n\nPlease check the Configuration tab."
                messagebox.showerror("Validation Error", error_msg)
                return False

        # Validate numeric inputs
        try:
            float(self.page_width.get())
            float(self.margin.get())
            float(self.font_size.get())
            float(self.header_font_size.get())
        except ValueError:
            messagebox.showerror("Error", "All numeric values must be valid numbers")
            return False

        return True

    def start_processing(self):
        """Start the processing operation."""
        if not self.validate_inputs():
            return

        # Reset stop event
        self.stop_event.clear()
        self.is_processing = True

        # Update UI state
        self.process_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.status_var.set("Processing...")
        self.progress_var.set(0)

        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self.process_files)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def stop_processing(self):
        """Stop the current processing operation."""
        if self.is_processing:
            logging.info("Stop requested by user...")
            self.stop_event.set()
            self.stop_btn.configure(state='disabled')
            self.status_var.set("Stopping...")

    def process_files(self):
        """Process files in a separate thread."""
        try:
            # Import here to avoid circular imports
            from main import main as process_main

            # Create configuration from GUI values
            config = GUIConfig(
                input_folder=Path(self.input_folder.get()),
                output_folder=Path(self.output_folder.get()),
                final_output=self.output_filename.get(),
                sort_mode=self.sort_mode.get(),
                page_width_mm=float(self.page_width.get()),
                margin_mm=float(self.margin.get()),
                font_size=float(self.font_size.get()),
                header_font_size=float(self.header_font_size.get())
            )

            # Log current mode
            logging.info(f"Processing with sort mode: {config.sort_mode}")

            # Get total number of files for progress
            total_files = len(list(config.input_folder.glob("*.rtf")))
            if total_files == 0:
                raise ValueError("No RTF files found in input folder")

            # Define progress callback
            def update_progress(value, file_progress=None):
                if self.stop_event.is_set():
                    return
                self.root.after(0, lambda: self.progress_var.set(value))

            # Pass session state for ICH/Custom modes
            session_state = self.session_state if config.sort_mode in ["ich", "custom"] else None

            # Run the main process
            result = process_main(
                config=config,
                session_state=session_state,
                progress_callback=update_progress,
                stop_event=self.stop_event,
                parallel_workers=self.parallel_workers.get()
            )

            # Handle the result
            if result is None:
                success = True
                conversion_stats = None
            elif isinstance(result, tuple) and len(result) == 2:
                success, conversion_stats = result
            else:
                success = result
                conversion_stats = None

            if self.stop_event.is_set():
                self.root.after(0, self.processing_stopped)
            else:
                self.root.after(0, self.processing_complete, success, conversion_stats)

        except Exception as e:
            logging.error(f"Error during processing: {e}")
            self.root.after(0, self.processing_complete, False, None)
        finally:
            self.cleanup_resources()

    def processing_complete(self, success, conversion_stats=None):
        """Handle processing completion."""
        self.is_processing = False
        self.process_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')

        if success:
            if conversion_stats and 'failed' in conversion_stats and conversion_stats['failed'] > 0:
                # Completed with errors
                total_files = conversion_stats.get('successful', 0) + conversion_stats.get('failed', 0)
                self.status_var.set(f"Processing completed with errors ({conversion_stats['failed']} failed)")
                self.progress_var.set(100)

                message = f"Processing completed with errors:\n\n"
                message += f"✓ Successfully converted: {conversion_stats.get('successful', 0)} files\n"
                message += f"✗ Failed to convert: {conversion_stats.get('failed', 0)} files\n"
                message += f"Total files processed: {total_files}\n\n"
                message += "Check the log for details about failed files."

                messagebox.showwarning("Completed with Errors", message)
            else:
                # All successful
                self.status_var.set("Processing completed successfully")
                self.progress_var.set(100)

                if conversion_stats:
                    message = f"All files processed successfully!\n\n"
                    message += f"✓ Files converted: {conversion_stats.get('successful', 0)}"
                    messagebox.showinfo("Success", message)
                else:
                    messagebox.showinfo("Success", "Processing completed successfully!")
        else:
            self.status_var.set("Processing failed")
            messagebox.showerror("Error", "Processing failed. Check the log for details.")

    def processing_stopped(self):
        """Handle processing being stopped by user."""
        self.is_processing = False
        self.process_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.status_var.set("Processing stopped by user")
        self.progress_var.set(0)
        messagebox.showinfo("Stopped", "Processing was stopped by user.")

    def cleanup_resources(self):
        """Clean up resources after processing."""
        try:
            gc.collect()
        except Exception as e:
            logging.debug(f"Cleanup error (non-critical): {e}")

    def on_closing(self):
        """Handle window closing."""
        if self.is_processing:
            if messagebox.askokcancel("Quit", "Processing is in progress. Do you want to stop and quit?"):
                self.stop_event.set()
                if self.processing_thread:
                    self.processing_thread.join(timeout=2)
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = RTF2PDFGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()