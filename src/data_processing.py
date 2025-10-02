#!/usr/bin/env python3
import logging
from pathlib import Path
from typing import Tuple
import concurrent.futures
import threading

import pandas as pd

# Import the converter function needed by convert_all
from src.rtf_converter import convert_rtf_to_pdf, cleanup_thread_resources

# Configure logging (can be configured globally in main if preferred)
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# —————————————————————————————————————————————————————————————————————————
# I/O FUNCTIONS
# —————————————————————————————————————————————————————————————————————————

def load_ich_categories_map(xlsx_path: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, dtype={"section_number": str})

    # Support both legacy (ICH_section_name) and new generic (section_label) column names
    if "section_label" in df.columns:
        section_col = "section_label"
    elif "ICH_section_name" in df.columns:
        section_col = "ICH_section_name"
        # Rename to generic name for consistency
        df = df.rename(columns={"ICH_section_name": "section_label"})
    else:
        raise KeyError(f"Neither 'section_label' nor 'ICH_section_name' found in {xlsx_path.name}")

    if "section_number" not in df.columns:
        raise KeyError(f"'section_number' not found in {xlsx_path.name}")

    return df[["section_number", "section_label"]]


# —————————————————————————————————————————————————————————————————————————
# PROCESSING LOOP
# —————————————————————————————————————————————————————————————————————————

def convert_all(final_df: pd.DataFrame, output_pdf_folder: Path, progress_callback=None, stop_event=None, max_workers=3) -> tuple[int, int]:
    """
    Convert all RTF files to PDFs using Word COM automation with parallel processing.
    
    Args:
        final_df: DataFrame containing file information
        output_pdf_folder: Path to output folder for PDFs
        progress_callback: Optional callback function to report progress
                         Called with (file_index, total_files)
                         Should return False to stop processing
        stop_event: Optional threading.Event to signal stop request
        max_workers: Maximum number of parallel conversion threads (default 3)
    
    Returns:
        Tuple of (successful_conversions, failed_conversions)
    """
    if final_df.empty:
        logging.warning("No files to convert.")
        return 0, 0
        
    total_files = len(final_df)
    successful = 0
    failed = 0
    completed = 0
    
    # Thread-safe counter
    counter_lock = threading.Lock()
    
    # Create list of conversion tasks
    conversion_tasks = []
    for index, row in final_df.iterrows():
        file_path = row['filepath']
        title = row['title']
        pdf_path = output_pdf_folder / f"{Path(file_path).stem}.pdf"
        conversion_tasks.append((file_path, pdf_path, title))
    
    def convert_single_file(task):
        """Convert a single file and return result."""
        file_path, pdf_path, title = task
        
        # Check for stop signal before starting
        if stop_event and stop_event.is_set():
            return False, file_path, "Stopped"
        
        try:
            # Convert RTF to PDF
            success = convert_rtf_to_pdf(str(file_path), str(pdf_path), title)
            if success:
                logging.info(f"Successfully converted {file_path.name}")
                return True, file_path, None
            else:
                logging.error(f"Failed to convert {file_path.name}")
                return False, file_path, "Conversion failed"
                
        except Exception as e:
            logging.error(f"Error converting {file_path.name}: {e}")
            return False, file_path, str(e)
    
    # Create a thread initializer that will be called once per thread
    def thread_initializer():
        """Initialize thread for COM operations."""
        # This function is called once when a thread starts
        # The Word app will be created on first use via _get_word_app()
        pass
    
    def thread_finalizer():
        """Clean up thread resources when thread is done."""
        try:
            cleanup_thread_resources()
        except Exception as e:
            logging.warning(f"Error during thread cleanup: {e}")
    
    # Use ThreadPoolExecutor for parallel processing
    # Note: COM objects need to be created in each thread, so we use threads not processes
    logging.info(f"Starting parallel conversion with {max_workers} workers...")
    
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers,
        initializer=thread_initializer
    ) as executor:
        # Submit all tasks
        future_to_task = {executor.submit(convert_single_file, task): task for task in conversion_tasks}
        
        # Process completed tasks
        for future in concurrent.futures.as_completed(future_to_task):
            # Check for stop signal
            if stop_event and stop_event.is_set():
                # Cancel remaining tasks
                for f in future_to_task:
                    f.cancel()
                logging.info("Conversion stopped by user")
                break
            
            try:
                success, file_path, error = future.result()
                
                with counter_lock:
                    completed += 1
                    if success:
                        successful += 1
                    else:
                        failed += 1
                    
                    # Report progress
                    if progress_callback:
                        should_continue = progress_callback(completed, total_files)
                        if should_continue is False:
                            # Progress callback requested stop
                            if stop_event:
                                stop_event.set()
                            
            except Exception as e:
                with counter_lock:
                    completed += 1
                    failed += 1
                logging.error(f"Unexpected error in conversion thread: {e}")
    
    # Log summary
    if stop_event and stop_event.is_set():
        logging.info(f"Conversion stopped: {successful} succeeded, {failed} failed, {total_files - completed} not processed")
    else:
        logging.info(f"All conversions completed: {successful} succeeded, {failed} failed")
    
    # Clean up any remaining thread resources
    # This is important because ThreadPoolExecutor reuses threads
    logging.debug("Cleaning up thread resources...")
    try:
        cleanup_thread_resources()
    except Exception as e:
        logging.warning(f"Error during final thread cleanup: {e}")
    
    return successful, failed


# —————————————————————————————————————————————————————————————————————————
# TOC DATA STRUCTURE GENERATION
# —————————————————————————————————————————————————————————————————————————

def create_toc_structure(final_df: pd.DataFrame) -> pd.DataFrame:
    """Sorts the merged/validated data and creates a TOC structure DataFrame.

    Args:
        final_df: DataFrame containing merged and validated data with columns
                  like 'section_number', 'filename_stem', 'section_label',
                  'title', 'filepath'.

    Returns:
        A DataFrame formatted for TOC generation with columns:
        'level' (int): 1 for header, 2 for entry.
        'text' (str): Text to display in TOC.
        'type' (str): 'header' or 'entry'.
        'filepath' (Path | None): Original RTF path for entries, None for headers.
        'filename_stem' (str | None): Filename stem for entries, None for headers.
    """
    logging.info("Sorting data and preparing TOC structure...")
    # Sort by section, then filename stem within the section
    df_sorted = final_df.sort_values(by=['section_number', 'filename_stem'])

    toc_rows = []
    last_section = None
    for index, row in df_sorted.iterrows():
        current_section = row['section_number']
        section_label = row['section_label']  # Generic column name for both ICH and Custom modes
        doc_title = row['title'] if pd.notna(row['title']) else row['filename_stem'] # Fallback title
        filepath_val = row['filepath'] # Use the correct column name from final_df
        filename_stem = row['filename_stem']

        # If this is the first row of a new section, add the section header
        if current_section != last_section:
            section_header_text = f"{current_section}  {section_label}"
            toc_rows.append({
                'level': 1,  # Level 1 for section headers
                'text': section_header_text,
                'type': 'header',
                'filepath': None, # Headers don't have a source file
                'filename_stem': None # Keep column consistent
            })
            last_section = current_section
            logging.debug(f"Added TOC header: {section_header_text}")

        # Add the document entry row
        toc_rows.append({
            'level': 2, # Level 2 for document entries
            'text': doc_title,
            'type': 'entry',
            'filepath': filepath_val, # Use 'filepath' key consistently
            'filename_stem': filename_stem # Add filename stem
        })
        logging.debug(f"Added TOC entry: {doc_title}")

    toc_data = pd.DataFrame(toc_rows)
    logging.info(f"Created TOC data structure with {len(toc_data)} entries.")
    return toc_data


def create_automatic_sections(titles_df: pd.DataFrame) -> pd.DataFrame:
    """Creates automatic sections based on filename prefixes.
    
    Args:
        titles_df: DataFrame containing file information with 'filename_stem' column
        
    Returns:
        DataFrame with added section information
    """
    # Create a copy to avoid modifying the original
    df = titles_df.copy()
    
    # Define section mappings
    section_mappings = {
        't': '1.Tables',
        'f': '2.Figures',
        'l': '3.Listings'
    }
    
    # Add section_number and section_label columns (generic names for all modes)
    df['section_number'] = None
    df['section_label'] = None

    # Assign sections based on filename prefix
    for prefix, section in section_mappings.items():
        mask = df['filename_stem'].str.lower().str.startswith(prefix)
        df.loc[mask, 'section_number'] = section.split('.')[0]  # Get the number part
        df.loc[mask, 'section_label'] = section.split('.')[1]  # Get the name part
    
    # Filter out files that don't match any prefix
    df = df[df['section_number'].notna()]
    
    if df.empty:
        logging.warning("No files matched the automatic section prefixes (t, f, l)")
    else:
        logging.info(f"Automatically assigned sections to {len(df)} files")
        
    return df 