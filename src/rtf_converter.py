import sys
import logging
import gc
from pathlib import Path
import threading

# Optional imports
try:
    import fitz  # PyMuPDF for bookmarks
except ImportError:
    fitz = None

# Only import com client if on Windows
if sys.platform == 'win32':
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        win32com = None
        pythoncom = None
else:
    win32com = None
    pythoncom = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

WD_FORMAT_PDF = 17  # Word constant

# Thread-local storage for Word instances
_thread_local = threading.local()

def _get_word_app():
    """Get or create a Word application instance for the current thread."""
    if not hasattr(_thread_local, 'word_app') or _thread_local.word_app is None:
        if sys.platform != 'win32':
            raise OSError("RTF→PDF conversion only supported on Windows.")
        
        if not win32com:
            raise ImportError("pywin32 is required for COM automation.")
        
        # Initialize COM for this thread
        try:
            pythoncom.CoInitialize()
        except Exception as e:
            logging.warning(f"COM already initialized or error: {e}")
        
        # Try to create Word application with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Create Word application for this thread
                _thread_local.word_app = win32com.client.DispatchEx("Word.Application")
                if _thread_local.word_app is None:
                    raise Exception("Word application object is None")
                    
                _thread_local.word_app.Visible = False
                _thread_local.word_app.DisplayAlerts = False
                logging.debug(f"Successfully created Word application instance for thread {threading.current_thread().name}")
                break
                
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} to create Word app failed: {e}")
                _thread_local.word_app = None
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1)  # Brief pause before retry
                else:
                    raise Exception(f"Failed to create Word application after {max_retries} attempts: {e}")
        
    return _thread_local.word_app

def _cleanup_word_app():
    """Clean up the Word application instance for the current thread."""
    if hasattr(_thread_local, 'word_app'):
        try:
            if _thread_local.word_app:
                logging.debug(f"Closing Word application for thread {threading.current_thread().name}")
                _thread_local.word_app.Quit()
        except Exception as e:
            logging.warning(f"Error closing Word application: {e}")
        finally:
            _thread_local.word_app = None
            # Delete the attribute entirely so next call will recreate
            delattr(_thread_local, 'word_app')
            
    # Uninitialize COM for this thread
    try:
        pythoncom.CoUninitialize()
        logging.debug(f"COM uninitialized for thread {threading.current_thread().name}")
    except Exception as e:
        logging.debug(f"COM uninitialize error (may already be uninitialized): {e}")

def _add_bookmark(pdf_path: Path, title: str) -> bool:
    """Open the PDF at pdf_path, add a top‐level bookmark, and overwrite it."""
    if not fitz:
        logging.warning("PyMuPDF not installed; skipping bookmark.")
        return False

    tmp_path = pdf_path.with_suffix(pdf_path.suffix + ".tmp")
    try:
        with fitz.open(pdf_path) as src, fitz.open() as dst:
            dst.insert_pdf(src)
            dst.set_toc([(1, title, 1)])
            dst.save(tmp_path, garbage=4, deflate=True)

        tmp_path.replace(pdf_path)
        logging.info(f"Bookmarked PDF saved: {pdf_path.name}")
        return True

    except Exception as err:
        logging.error(f"Failed to add bookmark: {err}")
        tmp_path.unlink(missing_ok=True)
        return False


def convert_rtf_to_pdf(rtf_path: str, pdf_path: str, title: str = None) -> bool:
    """
    Convert an RTF to PDF via Word COM; optionally add a bookmark.
    Returns True if conversion succeeded (bookmark failures don't fail conversion).
    """
    rtf = Path(rtf_path)
    pdf = Path(pdf_path)

    if sys.platform != 'win32':
        logging.error("RTF→PDF conversion only supported on Windows.")
        return False

    if not win32com:
        logging.error("pywin32 is required for COM automation.")
        return False

    # Ensure output directory exists
    pdf.parent.mkdir(parents=True, exist_ok=True)

    doc = None

    try:
        logging.info(f"Converting {rtf.name} → {pdf.name}")
        
        # Get Word app for this thread
        word = _get_word_app()

        # Ensure absolute paths are passed to Word
        rtf_abs = str(rtf.resolve())
        pdf_abs = str(pdf.resolve())

        doc = word.Documents.Open(rtf_abs, ReadOnly=True)
        doc.SaveAs(pdf_abs, FileFormat=WD_FORMAT_PDF)
        logging.info("PDF conversion succeeded.")

        return True

    except Exception as e:
        logging.error(f"Conversion error: {e}")
        return False

    finally:
        # Cleanly close Word document
        if doc:
            try:
                doc.Close(False)
            except Exception as doc_close_err:
                logging.warning(f"Error closing document for {rtf.name}: {doc_close_err}")
            finally:
                doc = None
        
        # Force garbage collection
        gc.collect()

def cleanup_thread_resources():
    """Clean up thread-local resources. Call this when a thread is done with conversions."""
    _cleanup_word_app()
    gc.collect()
