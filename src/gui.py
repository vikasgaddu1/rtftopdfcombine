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

        # Set application icon
        icon_path = Path(__file__).parent.parent / "img" / "rtf_to_pdf_primary.ico"
        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))

        # Start maximized for better visibility
        self.root.state('zoomed')

        # Set theme colors
        self.bg_color = "#f0f0f0"
        self.accent_color = "#007bff"
        self.success_color = "#28a745"
        self.warning_color = "#ffc107"
        self.danger_color = "#dc3545"
        self.root.configure(bg=self.bg_color)
        
        # Track keyboard shortcuts state
        self.shortcuts_enabled = True
        self.menu_state_cache = {}

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

        # Variables for main tab - start empty for production use
        self.input_folder = tk.StringVar(value="")
        self.output_folder = tk.StringVar(value="")
        self.output_filename = tk.StringVar(value="final_document_with_toc.pdf")

        # Sort mode variable
        self.sort_mode = tk.StringVar(value="default")
        self.previous_sort_mode = "default"  # Track previous mode for reverting

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

        # Track last save operation
        self.last_save_successful = False

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

        # Configure notebook tab styles for better visibility
        style.configure('TNotebook.Tab',
                       font=('TkDefaultFont', 11, 'bold'),
                       padding=[20, 10])

        # Configure sub-notebook (config tabs) with smaller font
        style.configure('Config.TNotebook.Tab',
                       font=('TkDefaultFont', 10),
                       padding=[15, 8])

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions."""
        # Global shortcuts
        self.root.bind('<Control-o>', lambda e: self.handle_shortcut(self.browse_input) if self.shortcuts_enabled else None)
        self.root.bind('<Control-s>', lambda e: self.handle_shortcut(self.export_config) if self.shortcuts_enabled else None)
        self.root.bind('<Control-i>', lambda e: self.handle_shortcut(self.import_config) if self.shortcuts_enabled else None)
        self.root.bind('<F5>', lambda e: self.handle_shortcut(self.start_processing) if self.shortcuts_enabled else None)
        self.root.bind('<Escape>', lambda e: self.stop_processing() if self.is_processing else (self.handle_shortcut(lambda: None) if self.shortcuts_enabled else None))
        self.root.bind('<F1>', lambda e: self.handle_shortcut(self.show_help) if self.shortcuts_enabled else None)
        self.root.bind('<F11>', lambda e: self.handle_shortcut(self.maximize_window) if self.shortcuts_enabled else None)
        
    def handle_shortcut(self, func):
        """Handle keyboard shortcut execution."""
        if self.shortcuts_enabled and not self.is_processing:
            func()

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
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # File menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Browse Input Folder", command=self.browse_input, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Import Config", command=self.import_config, accelerator="Ctrl+I")
        self.file_menu.add_command(label="Export Config", command=self.export_config, accelerator="Ctrl+S")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_closing)

        # Window menu
        self.window_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Window", menu=self.window_menu)
        self.window_menu.add_command(label="Maximize", command=self.maximize_window, accelerator="F11")
        self.window_menu.add_command(label="Restore", command=self.restore_window)

        # Help menu
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Keyboard Shortcuts", command=self.show_help, accelerator="F1")
        self.help_menu.add_separator()
        self.help_menu.add_command(label="About", command=self.show_about)

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
        ttk.Button(input_frame, text="Browse (Ctrl+O)", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)

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

        # Process buttons with hint
        button_container = ttk.Frame(main_frame)
        button_container.pack(pady=10)

        # Hint label for ICH/Custom modes (hidden initially for default mode)
        self.process_hint_label = ttk.Label(
            button_container,
            text="💡 Configure sections and file mappings in the Configuration tab, then return here to process",
            style='Info.TLabel'
        )
        # Don't pack initially - will be shown when ICH/Custom mode is selected

        button_frame = ttk.Frame(button_container)
        button_frame.pack()

        self.process_btn = ttk.Button(
            button_frame,
            text="▶ Process Files (F5)",
            command=self.start_processing,
            style='Process.TButton'
        )
        self.process_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹ Stop (Esc)",
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
        ttk.Button(self.config_buttons_frame, text="📥 Import Config (Ctrl+I)",
                  command=self.import_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.config_buttons_frame, text="📤 Export Config (Ctrl+S)",
                  command=self.export_config).pack(side=tk.LEFT, padx=5)

        # Hide config buttons initially (default mode is selected)
        self.config_buttons_frame.pack_forget()

        # Create notebook for configuration sub-tabs (with smaller tabs)
        self.config_notebook = ttk.Notebook(self.config_tab, style='Config.TNotebook')
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
            text="💡 Click Section to assign | Type to search | Tab to next file | Click Ignore to toggle | Regex examples: ^f.* (starts with f), .*01.* (contains 01)",
            font=('TkDefaultFont', 9, 'italic'),
            foreground='#666'
        )
        instructions.pack(fill=tk.X, padx=10, pady=(5, 0))

        # Filter status label (for showing regex errors)
        self.filter_status_label = ttk.Label(
            self.file_mapping_frame,
            text="",
            font=('TkDefaultFont', 8, 'italic'),
            foreground='#dc3545'  # Red color for errors
        )
        self.filter_status_label.pack(fill=tk.X, padx=10, pady=(0, 5))

        # Track active dropdown to prevent multiple
        self.active_dropdown = None

        # Filter frame
        filter_frame = ttk.Frame(self.file_mapping_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        # Filter variables
        self.filter_filename = tk.StringVar()
        self.filter_section = tk.StringVar()
        self.filter_status = tk.StringVar()
        self.filter_use_regex = tk.BooleanVar(value=False)

        # Filter entries with labels
        ttk.Label(filter_frame, text="Filter:", font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)

        ttk.Label(filter_frame, text="File Name:").grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        filename_filter = ttk.Entry(filter_frame, textvariable=self.filter_filename, width=20)
        filename_filter.grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)

        # Section filter (will be shown/hidden based on mode)
        self.section_filter_label = ttk.Label(filter_frame, text="Section:")
        self.section_filter_label.grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)
        self.section_filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_section, width=25)
        self.section_filter_entry.grid(row=0, column=4, padx=5, pady=2, sticky=tk.W)

        ttk.Label(filter_frame, text="Status:").grid(row=0, column=5, padx=5, pady=2, sticky=tk.W)
        status_filter = ttk.Combobox(filter_frame, textvariable=self.filter_status, width=15, state='readonly')
        status_filter['values'] = ["All", "Mapped", "Not Mapped", "Ignored", "Ready"]
        status_filter.current(0)
        status_filter.grid(row=0, column=6, padx=5, pady=2, sticky=tk.W)

        # Regex checkbox
        regex_checkbox = ttk.Checkbutton(filter_frame, text="Use Regex", variable=self.filter_use_regex,
                                         command=self.apply_file_filters)
        regex_checkbox.grid(row=0, column=7, padx=5, pady=2)

        # Clear filters button
        ttk.Button(filter_frame, text="Clear Filters", command=self.clear_file_filters).grid(row=0, column=8, padx=5, pady=2)

        # Bind filter changes to refresh display
        self.filter_filename.trace('w', lambda *args: self.apply_file_filters())
        self.filter_section.trace('w', lambda *args: self.apply_file_filters())
        self.filter_status.trace('w', lambda *args: self.apply_file_filters())

        # Initially hide section filter in default mode
        if self.sort_mode.get() == "default":
            self.section_filter_label.grid_remove()
            self.section_filter_entry.grid_remove()

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

        # Bind events - single click for better UX
        self.files_tree.bind("<ButtonRelease-1>", self.on_file_click)
        self.files_tree.bind("<Return>", self.on_file_enter_key)
        self.files_tree.bind("<space>", self.on_file_space_key)

        # Toolbar for batch operations
        toolbar_frame = ttk.Frame(self.file_mapping_frame)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(toolbar_frame, text="Batch Operations:", font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(toolbar_frame, text="⚡ Quick Pattern",
                  command=self.open_quick_pattern_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar_frame, text="📋 Manage Rules",
                  command=self.open_pattern_rules_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar_frame, text="▶ Apply All Rules",
                  command=self.apply_all_pattern_rules).pack(side=tk.LEFT, padx=(0, 5))

        # Summary frame
        self.files_summary_frame = ttk.Frame(self.file_mapping_frame)
        self.files_summary_frame.pack(fill=tk.X, padx=10, pady=5)

        self.files_summary_label = ttk.Label(
            self.files_summary_frame,
            text="Files: 0 | Mapped: 0 | Ignored: 0 | Unmapped: 0"
        )
        self.files_summary_label.pack(anchor=tk.W)

    def on_file_click(self, event):
        """Handle click on file mapping table - improved single-click UX."""
        # Clean up any existing dropdown
        if self.active_dropdown:
            try:
                if self.active_dropdown.winfo_exists():
                    self.active_dropdown.destroy()
            except:
                pass
            self.active_dropdown = None

        region = self.files_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.files_tree.identify_column(event.x)
            item = self.files_tree.identify_row(event.y)

            if not item:
                return

            # Force focus to the tree to ensure responsiveness
            self.files_tree.focus_set()

            # Column mapping depends on mode
            mode = self.sort_mode.get()

            if mode == "default":
                # Default mode: filename(#1), ignore(#2), status(#3)
                if column == "#2":
                    # Ignore column in default mode
                    self.root.after(1, lambda: self.toggle_file_ignore(item))
            else:
                # ICH/Custom mode: filename(#1), section(#2), ignore(#3), status(#4)
                if column == "#3":
                    # Ignore column in ICH/Custom mode
                    self.root.after(1, lambda: self.toggle_file_ignore(item))
                elif column == "#2":
                    # Section column - open dropdown
                    self.root.after(1, lambda: self.edit_file_section(item, event.x, event.y))

    def on_file_enter_key(self, event):
        """Handle Enter key - edit selected row's section (only in ICH/Custom mode)."""
        # Only allow section editing in ICH/Custom mode
        if self.sort_mode.get() == "default":
            return "break"

        selection = self.files_tree.selection()
        if selection:
            item = selection[0]
            bbox = self.files_tree.bbox(item, column="#2")
            if bbox:
                self.edit_file_section(item, bbox[0], bbox[1])
        return "break"

    def on_file_space_key(self, event):
        """Handle Space key - toggle ignore on selected row."""
        selection = self.files_tree.selection()
        if selection:
            self.toggle_file_ignore(selection[0])
        return "break"

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
            # Force UI update to prevent click timing issues
            self.files_tree.update_idletasks()

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
            width=50,
            state='normal'  # Ensure it's editable for typing
        )

        # Set current value
        if current_section and current_section != "Not Mapped":
            combo.set(current_section)
        else:
            combo.set("")

        # Store all values for filtering
        all_values = section_values.copy()
        
        # Track if dropdown is open
        dropdown_open = False

        # Position the combobox (make it wider than the column for better visibility)
        combo.place(x=bbox[0], y=bbox[1], width=min(450, bbox[2] + 150), height=bbox[3])
        combo.focus()
        combo.focus_set()  # Ensure focus is set

        # Open dropdown immediately after placing
        def open_dropdown():
            nonlocal dropdown_open
            try:
                # Force dropdown to open by simulating a button press
                combo.event_generate('<Button-1>')
                combo.event_generate('<ButtonRelease-1>')
                dropdown_open = True
            except:
                pass
        
        # Open dropdown after widget is fully placed
        self.root.after(10, open_dropdown)

        def on_keyrelease(event):
            """Filter dropdown as user types."""
            nonlocal dropdown_open
            
            # Don't filter for special keys
            if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Tab', 'Return', 'Escape']:
                return
                
            typed = combo.get().lower()
            
            if typed == "":
                combo['values'] = all_values
                filtered = all_values
            else:
                # Filter values based on typed text (search anywhere in the string)
                filtered = [v for v in all_values if typed in v.lower()]
                
            # Update dropdown with filtered values
            if filtered:
                combo['values'] = filtered
            else:
                # No matches
                combo['values'] = ["No matches found"]
                
            # Always try to keep dropdown open when typing
            try:
                # Force dropdown to reopen with new values
                combo.event_generate('<Button-1>')
                combo.event_generate('<ButtonRelease-1>')
                dropdown_open = True
            except:
                pass
                    
        def on_dropdown_close(event):
            """Track when dropdown closes."""
            nonlocal dropdown_open
            dropdown_open = False

        def save_and_close():
            """Save the selection and close dropdown."""
            selected = combo.get()
            if selected and selected in all_values:
                # Extract section number
                section_number = selected.split(" - ")[0]
                mapping.section_number = section_number
                logging.info(f"Mapped file '{filename}' to section '{section_number}'")
                self.refresh_file_mapping_row(item, mapping)
                self.update_files_summary()
                self.update_sections_summary()
            if self.active_dropdown == combo:
                self.active_dropdown = None
            try:
                combo.destroy()
            except:
                pass

        def on_select(event):
            """Handle selection from dropdown."""
            # Only save if a valid value was selected
            if combo.get() in all_values:
                save_and_close()

        def on_return(event):
            """Handle Enter key."""
            # If there's a single filtered match, select it
            current_values = combo['values']
            typed = combo.get()
            
            if typed and current_values and len(current_values) == 1 and current_values[0] != "No matches found":
                combo.set(current_values[0])
            
            save_and_close()
            return "break"

        def on_tab(event):
            """Handle Tab key - save and move to next file."""
            save_and_close()
            # Move to next item
            next_item = self.files_tree.next(item)
            if next_item:
                self.files_tree.selection_set(next_item)
                self.files_tree.focus(next_item)
                self.files_tree.see(next_item)
                # Open dropdown for next item after short delay
                next_bbox = self.files_tree.bbox(next_item, column="#2")
                if next_bbox:
                    self.root.after(50, lambda: self.edit_file_section(next_item, next_bbox[0], next_bbox[1]))
            return "break"

        def on_escape(event):
            """Handle Escape - cancel without saving."""
            if self.active_dropdown == combo:
                self.active_dropdown = None
            try:
                combo.destroy()
            except:
                pass
            return "break"

        def on_focusout(event):
            """Handle focus loss."""
            # Check if focus went to dropdown list (which is ok)
            try:
                focused = self.root.focus_get()
                if focused and focused != combo:
                    # Delay to allow click events to process
                    self.root.after(200, lambda: combo.destroy() if combo.winfo_exists() else None)
                    if self.active_dropdown == combo:
                        self.active_dropdown = None
            except:
                pass

        # Store as active dropdown
        self.active_dropdown = combo

        # Bind events
        combo.bind("<KeyRelease>", on_keyrelease)
        combo.bind("<<ComboboxSelected>>", on_select)
        combo.bind("<Return>", on_return)
        combo.bind("<Tab>", on_tab)
        combo.bind("<Escape>", on_escape)
        combo.bind("<FocusOut>", on_focusout)
        combo.bind("<<ComboboxClosed>>", on_dropdown_close)

    def refresh_file_mapping_row(self, item, mapping):
        """Refresh a single row in the file mapping table."""
        # Get current mode
        mode = self.sort_mode.get()
        
        # Get section label
        section_display = "Not Mapped"
        if mapping.section_number:
            section = self.session_state.get_section(mapping.section_number)
            if section:
                section_display = f"{section.section_number} - {section.section_label}"

        # Get status with emoji (adjust for default mode)
        if mode == "default":
            # Default mode: no mapping needed, just ready or ignored
            status_text = "🚫 Ignored" if mapping.ignore else "📄 Ready"
        else:
            # ICH/Custom mode: show mapping status
            status_text = {
                "mapped": "✅ Mapped",
                "unmapped": "⚠️ Not Mapped",
                "ignored": "🚫 Ignored"
            }.get(mapping.status, mapping.status)

        # Get ignore display with visible checkbox
        ignore_display = "☑" if mapping.ignore else "☐"

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

    def clear_file_filters(self):
        """Clear all file mapping filters."""
        self.filter_filename.set("")
        self.filter_section.set("")
        self.filter_status.set("All")
        # apply_file_filters will be called automatically via trace

    def apply_file_filters(self):
        """Apply filters to the file mapping table."""
        # Check if filters are initialized yet
        if not hasattr(self, 'filter_filename'):
            return

        # Get filter values
        filename_filter = self.filter_filename.get()
        section_filter = self.filter_section.get()
        status_filter = self.filter_status.get()
        use_regex = self.filter_use_regex.get()

        mode = self.sort_mode.get()

        # Debug log filter state
        if filename_filter or section_filter:
            logging.debug(f"Applying filters - Filename: '{filename_filter}', Section: '{section_filter}', Regex: {use_regex}")

        # Clear existing items
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)

        # Track filtered count
        filtered_count = 0
        total_count = len(self.session_state.file_mappings)

        # Compile regex patterns if enabled
        filename_pattern = None
        section_pattern = None
        regex_error = None

        if use_regex:
            import re
            try:
                if filename_filter:
                    filename_pattern = re.compile(filename_filter, re.IGNORECASE)
                    logging.debug(f"Compiled filename regex: {filename_filter}")
            except re.error as e:
                logging.warning(f"Invalid filename regex '{filename_filter}': {e}")
                regex_error = f"Invalid filename regex: {e}"
                filename_pattern = None

            try:
                if section_filter:
                    section_pattern = re.compile(section_filter, re.IGNORECASE)
                    logging.debug(f"Compiled section regex: {section_filter}")
            except re.error as e:
                logging.warning(f"Invalid section regex '{section_filter}': {e}")
                if regex_error:
                    regex_error += f" | Invalid section regex: {e}"
                else:
                    regex_error = f"Invalid section regex: {e}"
                section_pattern = None

        # Update filter status label
        if hasattr(self, 'filter_status_label'):
            if regex_error:
                self.filter_status_label.config(text=f"⚠ {regex_error}", foreground='#dc3545')
            elif use_regex and (filename_filter or section_filter):
                self.filter_status_label.config(text="✓ Using regex patterns", foreground='#28a745')
            else:
                self.filter_status_label.config(text="", foreground='#666')

        # Add files from session state that match filters
        for mapping in self.session_state.file_mappings:
            # Get section label
            section_display = "Not Mapped"
            if mapping.section_number:
                section = self.session_state.get_section(mapping.section_number)
                if section:
                    section_display = f"{section.section_number} - {section.section_label}"

            # Get status (adjust for default mode)
            if mode == "default":
                # Default mode: no mapping needed, just ready or ignored
                status_text = "🚫 Ignored" if mapping.ignore else "📄 Ready"
            else:
                # ICH/Custom mode: show mapping status
                status_text = {
                    "mapped": "✅ Mapped",
                    "unmapped": "⚠️ Not Mapped",
                    "ignored": "🚫 Ignored"
                }.get(mapping.status, mapping.status)

            # Apply filters
            if filename_filter:
                if use_regex and filename_pattern:
                    if not filename_pattern.search(mapping.filename):
                        logging.debug(f"Regex filter excluded: {mapping.filename}")
                        continue
                    else:
                        logging.debug(f"Regex filter matched: {mapping.filename}")
                else:
                    if filename_filter.lower() not in mapping.filename.lower():
                        continue

            if section_filter:
                if use_regex and section_pattern:
                    if not section_pattern.search(section_display):
                        continue
                else:
                    if section_filter.lower() not in section_display.lower():
                        continue

            if status_filter != "All":
                # Map status filter to actual status text
                status_map = {
                    "Mapped": "✅ Mapped",
                    "Not Mapped": "⚠️ Not Mapped",
                    "Ignored": "🚫 Ignored",
                    "Ready": "📄 Ready"
                }
                if status_filter in status_map and status_text != status_map[status_filter]:
                    continue

            # File passes all filters, add it
            filtered_count += 1
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

        # Update summary with filter info
        self.update_files_summary_with_filter(filtered_count, total_count)

    def update_files_summary_with_filter(self, filtered_count, total_count):
        """Update the files summary label with filter information."""
        stats = self.session_state.get_statistics()
        summary_text = (
            f"Files: {stats['total_files']} | "
            f"Mapped: {stats['mapped_files']} | "
            f"Ignored: {stats['ignored_files']} | "
            f"Unmapped: {stats['unmapped_files']}"
        )

        if filtered_count < total_count:
            summary_text += f" | Showing: {filtered_count} of {total_count}"

        self.files_summary_label.config(text=summary_text)

    def refresh_file_mapping_display(self):
        """Refresh the entire file mapping table."""
        # Hide/show section column based on mode
        mode = self.sort_mode.get()
        if mode == "default":
            # Hide section column in default mode
            self.files_tree["displaycolumns"] = ("filename", "ignore", "status")
            # Hide section filter widgets
            if hasattr(self, 'section_filter_label'):
                self.section_filter_label.grid_remove()
                self.section_filter_entry.grid_remove()
        else:
            # Show all columns in ICH/Custom mode
            self.files_tree["displaycolumns"] = ("filename", "section", "ignore", "status")
            # Show section filter widgets
            if hasattr(self, 'section_filter_label'):
                self.section_filter_label.grid()
                self.section_filter_entry.grid()

        # Debug: Log number of ignored files before display
        ignored_count = sum(1 for m in self.session_state.file_mappings if m.ignore)
        logging.info(f"refresh_file_mapping_display: Displaying {len(self.session_state.file_mappings)} files, {ignored_count} are ignored")

        # Apply filters instead of showing all
        self.apply_file_filters()

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

        # Separator
        ttk.Separator(button_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Bulk import button
        ttk.Button(button_frame, text="📊 Import from Excel",
                  command=self.bulk_import_sections).pack(side=tk.LEFT, padx=5)

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

    def bulk_import_sections(self):
        """Import sections in bulk from Excel file."""
        # Import dialog
        from src.bulk_import_dialog import BulkSectionImportDialog

        dialog = BulkSectionImportDialog(self.root, self.session_state)
        result = dialog.show()

        # Refresh display if sections were imported
        if result and result.success and result.imported_count > 0:
            logging.info(f"Bulk import completed: {result.imported_count} sections imported")
            logging.info(f"Total sections in session state: {len(self.session_state.section_definitions)}")

            # Refresh sections display
            self.refresh_sections_display()

            # Also refresh file mapping display to update dropdowns
            self.refresh_file_mapping_display()

            # Force UI update
            self.root.update_idletasks()

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

    def has_configuration_changes(self):
        """Check if there are unsaved configuration changes."""
        # If there are any file mappings or section definitions, consider it as having changes
        if len(self.session_state.section_definitions) > 0:
            return True
        if any(m.section_number is not None for m in self.session_state.file_mappings):
            return True
        if any(m.ignore for m in self.session_state.file_mappings):
            return True
        return False

    def show_sort_mode_change_dialog(self, old_mode, new_mode):
        """Show dialog asking user what to do with unsaved changes when changing sort mode.

        Returns:
            'save': User wants to save before switching
            'switch': User wants to switch without saving
            'cancel': User wants to cancel the mode change
        """
        # Create custom dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Unsaved Configuration")
        dialog.geometry("500x180")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        result = tk.StringVar(value="cancel")

        # Message
        mode_names = {"default": "Default", "ich": "ICH", "custom": "Custom"}
        message = f"You have unsaved configuration changes in {mode_names.get(old_mode, old_mode)} mode.\n\n"
        message += f"What would you like to do before switching to {mode_names.get(new_mode, new_mode)} mode?"

        ttk.Label(dialog, text=message, wraplength=450, justify=tk.LEFT).pack(pady=20, padx=20)

        # Buttons frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10, padx=20, fill=tk.X)

        def on_save():
            result.set("save")
            dialog.destroy()

        def on_switch():
            result.set("switch")
            dialog.destroy()

        def on_cancel():
            result.set("cancel")
            dialog.destroy()

        # Create buttons with better visibility
        save_btn = ttk.Button(button_frame, text="💾 Save & Switch", command=on_save)
        save_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        ttk.Button(button_frame, text="Switch Without Saving", command=on_switch).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Bind Escape to cancel
        dialog.bind("<Escape>", lambda e: on_cancel())

        # Wait for dialog to close
        dialog.wait_window()

        return result.get()

    def verify_save_completed(self):
        """Check if the last save operation completed successfully.

        Returns True if save completed, False if user cancelled.
        """
        return self.last_save_successful

    def on_sort_mode_change(self):
        """Handle sort mode selection change."""
        new_mode = self.sort_mode.get()
        old_mode = self.previous_sort_mode

        # If mode hasn't actually changed, do nothing
        if new_mode == old_mode:
            return

        # Check if there are unsaved changes in ICH or Custom modes
        if old_mode in ["ich", "custom"] and self.has_configuration_changes():
            # Show warning dialog in a loop until user makes a valid choice
            while True:
                result = self.show_sort_mode_change_dialog(old_mode, new_mode)

                if result == "save":
                    # Save configuration before switching
                    self.export_config()
                    # After save, check if user actually saved or cancelled
                    if self.verify_save_completed():
                        # Save successful, break out of loop and continue with mode change
                        break
                    else:
                        # User cancelled the save dialog, show warning dialog again
                        logging.info("User cancelled save dialog, returning to mode change dialog")
                        continue
                elif result == "cancel":
                    # Revert to previous mode
                    self.sort_mode.set(old_mode)
                    return
                else:  # result == "switch"
                    # Continue without saving
                    break

        # Update previous mode tracker
        self.previous_sort_mode = new_mode

        # Reset everything when changing modes
        self.reset_ui_state()

        self.session_state.set_sort_mode(new_mode)

        # Show/hide configuration buttons and tab
        if new_mode in ["ich", "custom"]:
            self.config_buttons_frame.pack(fill=tk.X, pady=5)
            # Show hint label for ICH/Custom modes
            self.process_hint_label.pack(pady=(0, 5))

            # Load ICH sections if ICH mode selected
            if new_mode == "ich":
                self.load_ich_sections()
            else:
                # Custom mode - clear sections for user to define
                self.session_state.section_definitions.clear()
                self.refresh_sections_display()

            # Scan RTF files for both ICH and Custom modes
            self.scan_rtf_files()
        else:
            # Default mode
            self.config_buttons_frame.pack_forget()
            # Hide hint label for Default mode
            self.process_hint_label.pack_forget()
            # Clear sections (not needed for default mode)
            self.session_state.section_definitions.clear()
            # But scan RTF files so File Mapping tab can show files with Ignore checkbox
            self.scan_rtf_files()

        # Update configuration tab visibility
        self.update_config_tab_visibility()

        logging.info(f"Sort mode changed to: {new_mode}")

    def reset_ui_state(self):
        """Reset UI state when changing sort modes."""
        # Only reset if UI elements exist (not during initialization)
        if not hasattr(self, 'log_text'):
            return

        # Reset progress bar
        self.progress_var.set(0)

        # Reset status
        self.status_var.set("Ready")

        # Clear log output
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

    def update_config_tab_visibility(self):
        """Show/hide configuration tab based on sort mode."""
        mode = self.sort_mode.get()

        # Configuration tab is now available for all modes (default, ich, custom)
        # Enable Configuration tab for all modes
        self.notebook.tab(1, state="normal")

        # Show/hide Section Definition tab within Configuration based on mode
        if mode == "default":
            # Default mode: Only show File Mapping tab (hide Section Definition)
            try:
                tab_index = self.config_notebook.index(self.section_def_frame)
                # Tab exists and is visible, hide it
                self.config_notebook.hide(tab_index)
                logging.debug("Section Definition tab hidden for default mode")
            except tk.TclError:
                # Tab is already hidden or doesn't exist
                pass
        else:
            # ICH/Custom mode: Show both tabs
            # The simplest approach: just add the tab back
            # If it's already visible, this will move it. If hidden, it will show it.
            # Adding at the end ensures it appears after File Mapping
            try:
                # Remove it first if it exists (whether visible or hidden)
                self.config_notebook.forget(self.section_def_frame)
                logging.debug("Removed existing Section Definition tab")
            except:
                pass

            # Now add it back (this will make it visible)
            self.config_notebook.add(self.section_def_frame, text="Section Definition")
            logging.info("Section Definition tab shown for ICH/Custom mode")

    def load_ich_sections(self):
        """Load default ICH sections into session state."""
        sections = load_default_ich_sections()
        self.session_state.section_definitions = sections
        logging.info(f"Loaded {len(sections)} ICH sections")
        self.refresh_sections_display()

    def on_input_folder_change(self, *args):
        """Handle input folder change."""
        # Only scan if there's a valid folder path
        # Prevents scanning on initialization when folder is empty
        folder_path = self.input_folder.get().strip()
        if folder_path and Path(folder_path).exists():
            # Scan RTF files for all modes (default, ich, custom)
            # Default mode needs files for ignore functionality
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
                # Load config first to get the input folder path
                with open(file_path, 'r', encoding='utf-8') as f:
                    import json
                    config = json.load(f)

                # Get input folder from config if available
                input_folder_path = None
                if 'settings' in config and 'input_folder' in config['settings']:
                    input_folder_path = Path(config['settings']['input_folder'])
                else:
                    # Fall back to current input folder
                    input_folder_path = Path(self.input_folder.get())

                # IMPORTANT: Scan RTF files BEFORE importing using the correct path
                # Otherwise import_from_json will clear rtf_files and matching will fail
                if input_folder_path and input_folder_path.exists():
                    rtf_files = list(input_folder_path.glob("*.rtf"))
                    self.session_state.rtf_files = rtf_files
                    logging.info(f"Pre-import: Found {len(rtf_files)} RTF files for matching")
                else:
                    logging.warning(f"Input folder not found: {input_folder_path}")

                summary = self.session_state.import_from_json(Path(file_path))
                
                # Update sort mode in GUI to match imported config
                self.sort_mode.set(self.session_state.sort_mode)
                logging.info(f"Restored sort mode: {self.session_state.sort_mode}")

                # Restore settings if they exist in the imported config
                if 'settings' in summary and summary['settings']:
                    settings = summary['settings']
                    
                    # Restore paths
                    if 'input_folder' in settings:
                        self.input_folder.set(settings['input_folder'])
                    if 'output_folder' in settings:
                        self.output_folder.set(settings['output_folder'])
                    if 'output_filename' in settings:
                        self.output_filename.set(settings['output_filename'])
                    
                    # Restore PDF settings
                    if 'pdf_settings' in settings:
                        pdf_settings = settings['pdf_settings']
                        if 'page_width_mm' in pdf_settings:
                            self.page_width.set(pdf_settings['page_width_mm'])
                        if 'margin_mm' in pdf_settings:
                            self.margin.set(pdf_settings['margin_mm'])
                        if 'font_size' in pdf_settings:
                            self.font_size.set(pdf_settings['font_size'])
                        if 'header_font_size' in pdf_settings:
                            self.header_font_size.set(pdf_settings['header_font_size'])
                    
                    # Restore parallel workers
                    if 'parallel_workers' in settings:
                        self.parallel_workers.set(settings['parallel_workers'])
                    
                    logging.info("Imported configuration includes paths and PDF settings")

                # Show import summary
                message = f"Configuration Imported\n\n"
                message += f"Sections loaded: {summary['sections_loaded']}\n"
                message += f"Files matched: {summary['files_matched']}\n"

                if summary['files_not_in_config'] > 0:
                    message += f"Files not in config: {summary['files_not_in_config']} (unmapped)\n"

                if summary['files_in_config_but_missing'] > 0:
                    message += f"Files in config but missing: {summary['files_in_config_but_missing']}\n"

                if 'settings' in summary and summary['settings']:
                    message += "\n✓ Paths and PDF settings restored"
                
                message += "\n\nReview the Configuration tab to verify mappings."

                messagebox.showinfo("Import Successful", message)
                logging.info(f"Configuration imported from: {file_path}")

                # Update all displays
                self.refresh_sections_display()
                self.refresh_file_mapping_display()
                self.update_sections_summary()
                self.update_files_summary()
                
                # Debug: Check if ignore status was preserved
                ignored_count = sum(1 for m in self.session_state.file_mappings if m.ignore)
                logging.info(f"After import refresh: {ignored_count} files are marked as ignored")

            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import configuration:\n{str(e)}")
                logging.error(f"Failed to import configuration: {e}")

    def export_config(self):
        """Export current configuration to JSON file."""
        from datetime import datetime

        # Reset save status
        self.last_save_successful = False

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

                # Gather all settings to export
                additional_settings = {
                    "input_folder": self.input_folder.get(),
                    "output_folder": self.output_folder.get(),
                    "output_filename": self.output_filename.get(),
                    "pdf_settings": {
                        "page_width_mm": self.page_width.get(),
                        "margin_mm": self.margin.get(),
                        "font_size": self.font_size.get(),
                        "header_font_size": self.header_font_size.get()
                    },
                    "parallel_workers": self.parallel_workers.get()
                }

                self.session_state.export_to_json(Path(file_path), project_name, additional_settings)
                self.last_save_successful = True  # Mark save as successful
                messagebox.showinfo("Export Successful",
                                  f"Configuration exported to:\n{file_path}\n\n"
                                  f"Includes:\n"
                                  f"• Paths and filenames\n"
                                  f"• PDF settings\n"
                                  f"• Section definitions\n"
                                  f"• File mappings")
                logging.info(f"Configuration exported to: {file_path} (with all settings)")

            except Exception as e:
                self.last_save_successful = False  # Mark save as failed
                messagebox.showerror("Export Error", f"Failed to export configuration:\n{str(e)}")
                logging.error(f"Failed to export configuration: {e}")
        else:
            # User cancelled the save dialog
            self.last_save_successful = False

    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.DEBUG if __name__ == "__main__" else logging.INFO,
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
        # Check input folder is not empty
        input_folder_str = self.input_folder.get().strip()
        if not input_folder_str:
            messagebox.showerror("Error", "Please select an input folder")
            return False

        # Check input folder exists
        input_path = Path(input_folder_str)
        if not input_path.exists():
            messagebox.showerror("Error", "Input folder does not exist")
            return False

        # Check output folder is not empty
        output_folder_str = self.output_folder.get().strip()
        if not output_folder_str:
            messagebox.showerror("Error", "Please select an output folder")
            return False

        # Check/create output folder
        output_path = Path(output_folder_str)
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

    def lock_ui(self):
        """Lock UI controls during processing to prevent changes."""
        try:
            logging.info("=== LOCKING UI FOR PROCESSING ===")
            
            # Disable keyboard shortcuts except Escape for stop
            self.shortcuts_enabled = False
            logging.debug("Keyboard shortcuts disabled")
            
            # Change cursor to indicate processing
            self.root.configure(cursor="wait")
            logging.debug("Cursor changed to 'wait'")
            
            # Update window title to indicate processing
            self.root.title("RTF to PDF Converter with TOC - [PROCESSING...]")
            
            # Disable all menus
            self._disable_menus()
            logging.debug("Menus disabled")
            
            # Disable all widgets recursively
            widget_count = 0
            for widget in self.root.winfo_children():
                self._disable_widget_recursive(widget)
                widget_count += 1
            logging.debug(f"Disabled {widget_count} root-level widgets")

            # Keep stop button enabled (must be after recursive disable)
            self.stop_btn.configure(state='normal')
            logging.debug("Stop button kept enabled")
            
            # Force UI update WITHOUT blocking
            self.root.update_idletasks()
            
            logging.info("=== UI LOCKED SUCCESSFULLY ===")
        except Exception as e:
            logging.error(f"Error locking UI: {e}")
            # Even if there's an error, ensure stop button works
            try:
                self.stop_btn.configure(state='normal')
            except:
                pass

    def unlock_ui(self):
        """Unlock UI controls after processing."""
        logging.info("=== UNLOCKING UI AFTER PROCESSING ===")
        
        # Restore normal cursor
        self.root.configure(cursor="")
        logging.debug("Cursor restored to normal")
        
        # Re-enable keyboard shortcuts
        self.shortcuts_enabled = True
        logging.debug("Keyboard shortcuts enabled")
        
        # Re-enable menus
        self._enable_menus()
        logging.debug("Menus enabled")
        
        # Re-enable all widgets
        widget_count = 0
        for widget in self.root.winfo_children():
            self._enable_widget_recursive(widget)
            widget_count += 1
        logging.debug(f"Enabled {widget_count} root-level widgets")

        # Reset button states
        self.process_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        logging.debug("Button states reset")
        
        # Restore window title
        self.root.title("RTF to PDF Converter with TOC")
        
        # Force UI update
        self.root.update_idletasks()
        logging.info("=== UI UNLOCKED SUCCESSFULLY ===")

    def _disable_menus(self):
        """Disable all menu items during processing."""
        try:
            # Store current menu states and disable all except Exit
            menus = [self.file_menu, self.window_menu, self.help_menu]
            
            for menu in menus:
                if not hasattr(menu, '_menu_states'):
                    menu._menu_states = {}
                    
                # Get the number of menu items
                last = menu.index("end")
                if last is not None:
                    for i in range(last + 1):
                        try:
                            # Get the menu item type
                            item_type = menu.type(i)
                            if item_type in ['command', 'cascade', 'checkbutton', 'radiobutton']:
                                # Get current state
                                current_state = menu.entrycget(i, 'state')
                                menu._menu_states[i] = current_state
                                
                                # Check if it's the Exit command
                                label = menu.entrycget(i, 'label')
                                if label != 'Exit':
                                    menu.entryconfig(i, state='disabled')
                        except:
                            pass
        except Exception as e:
            logging.debug(f"Could not disable menus: {e}")

    def _enable_menus(self):
        """Re-enable all menu items after processing."""
        try:
            menus = [self.file_menu, self.window_menu, self.help_menu]
            
            for menu in menus:
                if hasattr(menu, '_menu_states'):
                    for i, state in menu._menu_states.items():
                        try:
                            menu.entryconfig(i, state=state)
                        except:
                            pass
                    # Clear stored states
                    delattr(menu, '_menu_states')
        except Exception as e:
            logging.debug(f"Could not enable menus: {e}")

    def _disable_widget_recursive(self, widget):
        """Recursively disable widgets while keeping them visible."""
        try:
            # Skip certain widgets
            if widget == self.stop_btn or widget == self.log_text:
                return

            widget_type = widget.winfo_class()

            # Only disable interactive widgets, not containers
            if widget_type in ('TButton', 'Button'):
                if widget != self.stop_btn:  # Double-check stop button
                    widget.configure(state='disabled')
            elif widget_type in ('TEntry', 'Entry'):
                widget.configure(state='readonly')  # Use readonly instead of disabled to keep visible
            elif widget_type in ('TCombobox', 'Combobox'):
                widget.configure(state='disabled')
            elif widget_type in ('TSpinbox', 'Spinbox'):
                widget.configure(state='readonly')  # Use readonly to keep visible
            elif widget_type in ('TRadiobutton', 'Radiobutton'):
                widget.configure(state='disabled')
            elif widget_type in ('TCheckbutton', 'Checkbutton'):
                widget.configure(state='disabled')
            elif widget_type == 'TNotebook':
                # Store current tab for restoration
                if not hasattr(widget, '_current_tab'):
                    widget._current_tab = widget.select()
                # Bind to prevent tab switching instead of disabling tabs
                widget.bind('<Button-1>', lambda e: "break", add="+")
            elif widget_type in ('Treeview', 'ttk::treeview'):
                # Store bindings for later restoration
                if not hasattr(widget, '_stored_bindings'):
                    widget._stored_bindings = True
                    # Override bindings to prevent interaction
                    widget.bind("<ButtonRelease-1>", lambda e: "break")
                    widget.bind("<Double-1>", lambda e: "break")
                    widget.bind("<Return>", lambda e: "break")
                    widget.bind("<space>", lambda e: "break")
            elif widget_type == 'Text':
                # Keep log text functional
                if widget != self.log_text:
                    widget.configure(state='disabled')
            # Don't disable frames, labels, or other container/display widgets
            elif widget_type in ('Frame', 'TFrame', 'Labelframe', 'TLabelframe', 
                                'Label', 'TLabel', 'Scrollbar', 'TScrollbar'):
                pass  # Keep these visible and functional

            # Recurse to children
            for child in widget.winfo_children():
                self._disable_widget_recursive(child)
                
        except Exception as e:
            logging.debug(f"Could not disable widget {widget}: {e}")

    def _enable_widget_recursive(self, widget):
        """Recursively enable widgets."""
        try:
            widget_type = widget.winfo_class()

            # Enable all interactive widgets
            if widget_type in ('TButton', 'Button'):
                # Keep stop button disabled after processing
                if widget != self.stop_btn:
                    widget.configure(state='normal')
            elif widget_type in ('TEntry', 'Entry'):
                widget.configure(state='normal')
            elif widget_type in ('TCombobox', 'Combobox'):
                widget.configure(state='readonly')  # Combobox should be readonly, not normal
            elif widget_type in ('TSpinbox', 'Spinbox'):
                widget.configure(state='normal')
            elif widget_type in ('TRadiobutton', 'Radiobutton'):
                widget.configure(state='normal')
            elif widget_type in ('TCheckbutton', 'Checkbutton'):
                widget.configure(state='normal')
            elif widget_type == 'TNotebook':
                # Remove the blocking binding
                widget.unbind('<Button-1>')
                # Restore the selected tab if stored
                if hasattr(widget, '_current_tab'):
                    try:
                        widget.select(widget._current_tab)
                        delattr(widget, '_current_tab')
                    except:
                        pass
            elif widget_type in ('Treeview', 'ttk::treeview'):
                # Restore tree interactions
                if hasattr(widget, '_stored_bindings'):
                    delattr(widget, '_stored_bindings')
                    # Re-bind original events
                    if widget == self.files_tree:
                        widget.bind("<ButtonRelease-1>", self.on_file_click)
                        widget.bind("<Return>", self.on_file_enter_key)
                        widget.bind("<space>", self.on_file_space_key)
                    elif widget == self.sections_tree:
                        widget.bind("<Double-1>", lambda e: self.edit_section())
            elif widget_type == 'Text':
                # Keep log text disabled, others enabled
                if widget == self.log_text:
                    widget.configure(state='disabled')
                else:
                    widget.configure(state='normal')
            # Don't need to enable frames, labels, etc. as they weren't disabled
            elif widget_type in ('Frame', 'TFrame', 'Labelframe', 'TLabelframe',
                                'Label', 'TLabel', 'Scrollbar', 'TScrollbar'):
                pass

            # Recurse to children
            for child in widget.winfo_children():
                self._enable_widget_recursive(child)
                
        except Exception as e:
            logging.debug(f"Could not enable widget {widget}: {e}")

    def start_processing(self):
        """Start the processing operation."""
        if not self.validate_inputs():
            return

        # Reset stop event
        self.stop_event.clear()
        self.is_processing = True

        # Lock UI to prevent changes during processing
        self.lock_ui()

        # Update status
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

            # Pass session state for all modes (needed for ignore functionality)
            # Default mode needs it to filter out ignored files
            session_state = self.session_state

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

        # Unlock UI
        self.unlock_ui()

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

        # Unlock UI
        self.unlock_ui()

        self.status_var.set("Processing stopped by user")
        self.progress_var.set(0)
        messagebox.showinfo("Stopped", "Processing was stopped by user.")

    def cleanup_resources(self):
        """Clean up resources after processing."""
        try:
            gc.collect()
        except Exception as e:
            logging.debug(f"Cleanup error (non-critical): {e}")

    def open_quick_pattern_dialog(self):
        """Open the quick pattern assignment dialog."""
        # Check if we're in a mode that supports pattern rules
        if self.sort_mode.get() == "default":
            messagebox.showinfo(
                "Pattern Rules Not Available",
                "Pattern rules are only available in ICH or Custom sort modes.\n\n"
                "Please switch to ICH or Custom mode in the Main tab.",
                parent=self.root
            )
            return

        # Check if sections are defined
        if not self.session_state.section_definitions:
            messagebox.showwarning(
                "No Sections Defined",
                "Please define sections in the Section Definition tab first.",
                parent=self.root
            )
            return

        # Get selected files
        selected_items = self.files_tree.selection()
        selected_files = []
        for item in selected_items:
            values = self.files_tree.item(item, 'values')
            if values:
                selected_files.append(values[0])  # filename is first column

        # Import and show dialog
        from src.pattern_dialogs import PatternQuickDialog
        dialog = PatternQuickDialog(self.root, self.session_state, selected_files)
        result = dialog.show()

        if result:
            # Refresh the file mapping display
            self.refresh_file_mapping_display()
            messagebox.showinfo(
                "Pattern Applied",
                f"Applied section {result['section_number']} to {len(result['matches'])} file(s)." +
                ("\nRule saved for future use." if result['saved_as_rule'] else ""),
                parent=self.root
            )

    def open_pattern_rules_dialog(self):
        """Open the pattern rules management dialog."""
        # Check if we're in a mode that supports pattern rules
        if self.sort_mode.get() == "default":
            messagebox.showinfo(
                "Pattern Rules Not Available",
                "Pattern rules are only available in ICH or Custom sort modes.\n\n"
                "Please switch to ICH or Custom mode in the Main tab.",
                parent=self.root
            )
            return

        # Check if sections are defined
        if not self.session_state.section_definitions:
            messagebox.showwarning(
                "No Sections Defined",
                "Please define sections in the Section Definition tab first.",
                parent=self.root
            )
            return

        # Import and show dialog
        from src.pattern_dialogs import PatternRulesDialog
        dialog = PatternRulesDialog(self.root, self.session_state)
        dialog.show()

        # Refresh the file mapping display in case rules were applied
        self.refresh_file_mapping_display()

    def apply_all_pattern_rules(self):
        """Apply all active pattern rules to file mappings."""
        # Check if we're in a mode that supports pattern rules
        if self.sort_mode.get() == "default":
            messagebox.showinfo(
                "Pattern Rules Not Available",
                "Pattern rules are only available in ICH or Custom sort modes.\n\n"
                "Please switch to ICH or Custom mode in the Main tab.",
                parent=self.root
            )
            return

        if not self.session_state.pattern_rule_manager.rules:
            messagebox.showinfo(
                "No Rules Defined",
                "No pattern rules have been defined yet.\n\n"
                "Use '⚡ Quick Pattern' or '📋 Manage Rules' to create pattern rules.",
                parent=self.root
            )
            return

        # Ask if should override existing mappings
        override = messagebox.askyesnocancel(
            "Apply Pattern Rules",
            "Override existing section assignments?\n\n"
            "Yes = Override all assignments\n"
            "No = Only unmapped files\n"
            "Cancel = Don't apply",
            parent=self.root
        )

        if override is None:
            return

        # Apply rules
        stats = self.session_state.pattern_rule_manager.apply_rules_to_mappings(
            self.session_state.file_mappings,
            override_existing=override
        )

        # Refresh display
        self.refresh_file_mapping_display()

        # Show results
        messagebox.showinfo(
            "Pattern Rules Applied",
            f"Pattern rules have been applied:\n\n"
            f"  • Applied: {stats['applied']} files\n"
            f"  • Skipped: {stats['skipped']} files\n"
            f"  • Failed: {stats['failed']} files",
            parent=self.root
        )

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