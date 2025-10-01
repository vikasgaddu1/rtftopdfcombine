import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from pathlib import Path
import threading
import queue
import sys
import os
import gc

# Import the GUI configuration
from src.gui_config import GUIConfig

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
        self.root.geometry("800x600")
        
        # Set theme colors
        self.bg_color = "#f0f0f0"
        self.accent_color = "#007bff"
        self.root.configure(bg=self.bg_color)
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create variables with default values
        self.input_folder = tk.StringVar(value=str(Path.cwd() / "input"))
        self.output_folder = tk.StringVar(value=str(Path.cwd() / "output"))
        self.output_filename = tk.StringVar(value="final_document_with_toc.pdf")
        self.use_section_file = tk.BooleanVar(value=False)
        self.section_file = tk.StringVar(value="")
        
        # Add PDF settings
        self.page_width = tk.StringVar(value="210")
        self.margin = tk.StringVar(value="15")
        self.font_size = tk.StringVar(value="8")
        self.header_font_size = tk.StringVar(value="10")
        self.parallel_workers = tk.IntVar(value=3)  # Default 3 workers
        
        # Processing control variables
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.is_processing = False
        
        # Create widgets
        self.create_widgets()
        
        # Set initial UI state for section file controls
        self.toggle_section_file()
        
        # Create progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.main_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=10)
        
        # Create log display
        self.create_log_display()
        
        # Set up logging
        self.setup_logging()
        
        # Create status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Cleanup when window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Input folder selection
        input_frame = ttk.LabelFrame(self.main_frame, text="Input Settings", padding="5")
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="Input Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.input_folder, width=70).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)
        
        # Output folder selection
        ttk.Label(input_frame, text="Output Folder:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.output_folder, width=70).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)
        
        # Output filename
        ttk.Label(input_frame, text="Output Filename:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.output_filename, width=70).grid(row=2, column=1, padx=5, pady=5)
        
        # Section file checkbox and entry
        ttk.Checkbutton(input_frame, text="Use Section File", variable=self.use_section_file, 
                       command=self.toggle_section_file).grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.section_file_entry = ttk.Entry(input_frame, textvariable=self.section_file, width=70, state='disabled')
        self.section_file_entry.grid(row=3, column=1, padx=5, pady=5)
        self.section_file_button = ttk.Button(input_frame, text="Browse", command=self.browse_section_file, state='disabled')
        self.section_file_button.grid(row=3, column=2, padx=5, pady=5)
        
        # PDF Options
        pdf_frame = ttk.LabelFrame(self.main_frame, text="PDF Options", padding="5")
        pdf_frame.pack(fill=tk.X, pady=5)
        
        # Add PDF options here based on pdf_utils.py settings
        ttk.Label(pdf_frame, text="Page Width (mm):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(pdf_frame, textvariable=self.page_width, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(pdf_frame, text="Margin (mm):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(pdf_frame, textvariable=self.margin, width=10).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(pdf_frame, text="Font Size:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(pdf_frame, textvariable=self.font_size, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(pdf_frame, text="Header Font Size:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(pdf_frame, textvariable=self.header_font_size, width=10).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Add parallel workers option
        ttk.Label(pdf_frame, text="Parallel Workers:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        worker_spinbox = ttk.Spinbox(pdf_frame, from_=1, to=10, textvariable=self.parallel_workers, width=10)
        worker_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(pdf_frame, text="(Number of RTF files to convert simultaneously)", 
                 font=('TkDefaultFont', 8, 'italic')).grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=5)
        
        # Buttons frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=10)
        
        # Process button
        self.process_btn = ttk.Button(
            button_frame,
            text="Process Files",
            command=self.start_processing,
            style='Accent.TButton'
        )
        self.process_btn.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        self.stop_btn = ttk.Button(
            button_frame,
            text="Stop",
            command=self.stop_processing,
            state='disabled',
            style='Stop.TButton'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Create custom style for accent button
        style = ttk.Style()
        style.configure('Accent.TButton', background=self.accent_color)
        style.configure('Stop.TButton', background='#dc3545')  # Red color for stop

    def create_log_display(self):
        log_frame = ttk.LabelFrame(self.main_frame, text="Log Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state='disabled')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def setup_logging(self):
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        
        # Redirect logging to the text widget
        self.log_handler = RedirectText(self.log_text)
        logging.getLogger().addHandler(logging.StreamHandler(self.log_handler))

    def browse_input(self):
        folder = filedialog.askdirectory(initialdir=self.input_folder.get())
        if folder:
            self.input_folder.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory(initialdir=self.output_folder.get())
        if folder:
            self.output_folder.set(folder)

    def toggle_section_file(self):
        """Enable/disable section file entry based on checkbox state."""
        state = 'normal' if self.use_section_file.get() else 'disabled'
        self.section_file_entry.configure(state=state)
        self.section_file_button.configure(state=state)

    def browse_section_file(self):
        """Open file dialog to select section file."""
        file_path = filedialog.askopenfilename(
            initialdir=self.input_folder.get(),
            title="Select Section File",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            self.section_file.set(file_path)

    def validate_inputs(self):
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
        
        # Check section file if enabled
        if self.use_section_file.get():
            if not self.section_file.get():
                messagebox.showerror("Error", "Please select a section file")
                return False
            section_path = Path(self.section_file.get())
            if not section_path.exists():
                messagebox.showerror("Error", "Section file does not exist")
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
        try:
            # Import here to avoid circular imports
            from main import main as process_main
            
            # Create configuration from GUI values
            config = GUIConfig(
                input_folder=Path(self.input_folder.get()),
                output_folder=Path(self.output_folder.get()),
                final_output=self.output_filename.get(),
                use_section_file=self.use_section_file.get(),
                section_file_path=Path(self.section_file.get()) if self.section_file.get() else None,
                section_file_name=Path(self.section_file.get()).name if self.section_file.get() else None,
                page_width_mm=float(self.page_width.get()),
                margin_mm=float(self.margin.get()),
                font_size=float(self.font_size.get()),
                header_font_size=float(self.header_font_size.get())
            )
            
            # Log current GUI state
            logging.info(f"GUI Section file checkbox state: {config.use_section_file}")
            if config.use_section_file:
                logging.info(f"GUI Section file path: {config.section_file_path}")
                logging.info(f"Using manual section mode with file: {config.section_file_name}")
            else:
                logging.info("Using automatic section mode based on filename prefixes")
            
            # Get total number of files for progress calculation
            total_files = len(list(config.input_folder.glob("*.rtf")))
            if total_files == 0:
                raise ValueError("No RTF files found in input folder")
            
            # Define progress callback
            def update_progress(value, file_progress=None):
                if self.stop_event.is_set():
                    return
                # Direct progress value from main.py
                self.root.after(0, lambda: self.progress_var.set(value))
            
            # Add parallel workers setting
            parallel_workers = self.parallel_workers.get()

            # Run the main process with configuration
            result = process_main(
                config=config,
                progress_callback=update_progress,
                stop_event=self.stop_event,
                parallel_workers=parallel_workers
            )
            
            # Handle the result
            if result is None:
                # Old behavior for backward compatibility
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
            # Ensure resources are cleaned up
            self.cleanup_resources()

    def processing_complete(self, success, conversion_stats=None):
        self.is_processing = False
        self.process_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        
        if success:
            # Check if we have conversion statistics
            if conversion_stats and 'failed' in conversion_stats and conversion_stats['failed'] > 0:
                # Processing completed but with some errors
                total_files = conversion_stats.get('successful', 0) + conversion_stats.get('failed', 0)
                self.status_var.set(f"Processing completed with errors ({conversion_stats['failed']} failed)")
                self.progress_var.set(100)
                
                # Show detailed message
                message = f"Processing completed with errors:\n\n"
                message += f"✓ Successfully converted: {conversion_stats.get('successful', 0)} files\n"
                message += f"✗ Failed to convert: {conversion_stats.get('failed', 0)} files\n"
                message += f"Total files processed: {total_files}\n\n"
                message += "Check the log for details about failed files."
                
                messagebox.showwarning("Completed with Errors", message)
            else:
                # All files processed successfully
                self.status_var.set("Processing completed successfully")
                self.progress_var.set(100)
                
                if conversion_stats:
                    message = f"All files processed successfully!\n\n"
                    message += f"✓ Files converted: {conversion_stats.get('successful', 0)}"
                    messagebox.showinfo("Success", message)
                else:
                    messagebox.showinfo("Success", "Files processed successfully!")
        else:
            # Critical failure
            self.status_var.set("Processing failed")
            
            if conversion_stats and (conversion_stats.get('successful', 0) > 0 or conversion_stats.get('failed', 0) > 0):
                # Some files were processed before failure
                message = f"Processing failed:\n\n"
                message += f"Files converted before failure: {conversion_stats.get('successful', 0)}\n"
                message += f"Files failed: {conversion_stats.get('failed', 0)}\n\n"
                message += "Check the log for error details."
                messagebox.showerror("Processing Failed", message)
            else:
                messagebox.showerror("Error", "Processing failed. Check the log for details.")

    def processing_stopped(self):
        self.is_processing = False
        self.process_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.status_var.set("Processing stopped by user")
        self.progress_var.set(0)  # Reset progress bar to 0
        messagebox.showinfo("Stopped", "Processing was stopped by user.")

    def cleanup_resources(self):
        """Clean up resources after processing."""
        try:
            # Force garbage collection
            gc.collect()
            
            # If on Windows, try to clean up any COM objects
            if sys.platform == 'win32':
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except:
                    pass
                    
            logging.info("Resources cleaned up")
        except Exception as e:
            logging.warning(f"Error during resource cleanup: {e}")

    def on_closing(self):
        """Handle window close event."""
        if self.is_processing:
            if messagebox.askokcancel("Quit", "Processing is in progress. Do you want to stop and quit?"):
                self.stop_event.set()
                # Wait a bit for thread to finish
                if self.processing_thread and self.processing_thread.is_alive():
                    self.processing_thread.join(timeout=2)
            else:
                return
        
        self.cleanup_resources()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = RTF2PDFGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 