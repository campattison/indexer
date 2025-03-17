"""
PDF to Text Splitter
===================

This script takes a PDF file from the 'initial_files' folder and splits it into separate text files.

Requirements:
------------
This script will automatically set up a virtual environment and install PyMuPDF.

How to Use:
----------
1. Place your PDF file in the 'initial_files' folder
2. Edit the setting at the bottom of this file:
   - pdf_name: The name of your PDF file (e.g., "my_book.pdf")
3. Run the script
4. Find your output text files in the 'intermediate_files/book_pages' folder
"""

import os
import sys
import subprocess
from pathlib import Path
import venv

def setup_virtual_environment():
    """Create and activate virtual environment, install required packages."""
    venv_path = Path("venv")
    
    # Create virtual environment if it doesn't exist
    if not venv_path.exists():
        print("Setting up virtual environment...")
        venv.create(venv_path, with_pip=True)
    
    # Determine the path to the Python executable in the virtual environment
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:  # macOS and Linux
        python_path = venv_path / "bin" / "python"
        pip_path = venv_path / "bin" / "pip"

    # Install required packages if not already installed
    try:
        # Try importing fitz to check if PyMuPDF is installed
        import fitz
    except ImportError:
        print("Installing required packages...")
        subprocess.check_call([str(pip_path), "install", "PyMuPDF"])
        
    return python_path

def restart_in_venv():
    """Restart the script in the virtual environment if not already running in it."""
    if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
        python_path = setup_virtual_environment()
        
        # Restart the script using the virtual environment's Python
        print("Restarting script in virtual environment...")
        os.execv(str(python_path), [str(python_path), __file__])

# Rest of your imports
try:
    import fitz  # PyMuPDF
except ImportError:
    restart_in_venv()

def ensure_folders_exist():
    """Create the necessary folders if they don't exist."""
    Path("initial_files").mkdir(exist_ok=True)
    Path("intermediate_files").mkdir(exist_ok=True)
    Path("intermediate_files/book_pages").mkdir(parents=True, exist_ok=True)

def split_pdf_to_files(pdf_name: str):
    """
    Split PDF into individual text files by page number.
    
    Args:
        pdf_name (str): Name of your PDF file (e.g., "my_book.pdf")
                       The file should be in the 'initial_files' folder
    """
    # Ensure all necessary folders exist
    ensure_folders_exist()
    
    # Set up input and output paths
    pdf_path = Path("initial_files") / pdf_name
    output_path = Path("intermediate_files/book_pages")
    
    # Check if PDF exists
    if not pdf_path.exists():
        print("\nERROR: PDF file not found!")
        print(f"Please make sure '{pdf_name}' is in the 'initial_files' folder")
        print(f"Current working directory: {os.getcwd()}")
        print("\nChecking 'initial_files' folder contents:")
        initial_files = list(Path("initial_files").glob("*"))
        if initial_files:
            print("Found these files:")
            for file in initial_files:
                print(f"  - {file.name}")
        else:
            print("The 'initial_files' folder is empty!")
        return
        
    try:
        print(f"Attempting to open PDF: {pdf_name}")
        doc = fitz.Document(str(pdf_path))
        print(f"Successfully opened PDF. Processing {len(doc)} pages...")
        
        # Process each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")  # Extract text while preserving layout
            
            if text.strip():  # Only save non-empty pages
                # Save to file named by page number
                file_path = output_path / f"page_{page_num + 1}.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"Saved page {page_num + 1}")
            else:
                print(f"Warning: Page {page_num + 1} appears to be empty")
        
        doc.close()
        print(f"\nSuccess! Text files have been saved to: {output_path}")
        
    except Exception as e:
        print(f"\nError processing PDF: {str(e)}")
        print("If you're seeing a permission error, try closing any open files or folders.")
        print(f"Current working directory: {os.getcwd()}")
        raise

if __name__ == "__main__":
    print("\nPDF to Text Splitter")
    print("===================")
    
    # ============= SETTINGS TO MODIFY =============
    # Add your PDF file name here (the PDF should be in the 'initial_files' folder)
    pdf_name = "edge_of_sentience.pdf"
    # ============================================

    try:
        # Run the PDF splitter
        split_pdf_to_files(pdf_name)
    except Exception as e:
        print("\nSomething went wrong! Here's what you can try:")
        print("1. Check that your PDF filename matches exactly (including case)")
        print("2. Make sure no other programs have the PDF or text files open")
        print("\nTechnical error details:")
        print(str(e))
    
    # Keep console window open if running as executable
    input("\nPress Enter to exit...")

"""
Folder Structure:
---------------
project_folder/
    ├── initial_files/         # Put your PDF here
    ├── intermediate_files/    
    │   └── book_pages/       # Output text files go here
    └── 1_pdf_splitter.py     # This script
"""