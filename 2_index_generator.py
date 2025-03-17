"""
Index Generator
=============

This script generates an index from text files using OpenAI's GPT-4.

Requirements:
------------
This script will automatically use the virtual environment from pdf_splitter
and install required packages (openai, tqdm, python-dotenv).
"""

import os
import sys
import subprocess
from pathlib import Path
import venv
import json
import logging
import time
from dotenv import load_dotenv  # Import the load_dotenv function

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

    # Install required packages
    print("Installing required packages...")
    subprocess.check_call([str(pip_path), "install", "openai>=1.0.0", "tqdm", "python-dotenv"])
        
    return python_path

def restart_in_venv():
    """Restart the script in the virtual environment if not already running in it."""
    if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
        python_path = setup_virtual_environment()
        
        # Restart the script using the virtual environment's Python
        print("Restarting script in virtual environment...")
        os.execv(str(python_path), [str(python_path), __file__])

# Make sure we're in the virtual environment and have required packages
if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
    restart_in_venv()

# Load environment variables from .env file
load_dotenv()

# Now we can safely import our required packages
from openai import OpenAI
from tqdm import tqdm

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable is not set!")
    print("Please set your OpenAI API key in the .env file or as an environment variable.")
    sys.exit(1)

def setup_logging():
    """Set up logging to a file in the logs directory."""
    logs_path = Path('intermediate_files')
    os.makedirs(logs_path, exist_ok=True)
    log_file = logs_path / 'index_generator.log'

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("Logging setup complete.")

def clean_response_content(content):
    """Remove Markdown code block formatting from the response content."""
    if content.startswith('```'):
        # Split by lines and remove markdown wrapper
        lines = content.split('\n')
        # Remove first and last lines (markdown markers)
        content_lines = [line for line in lines if not line.startswith('```')]
        content = '\n'.join(content_lines)
    return content

def validate_json_structure(entry):
    """Validate the structure of an index entry."""
    required_fields = {'term', 'type', 'pages', 'original_term'}
    if not all(field in entry for field in required_fields):
        return False
    if not isinstance(entry['pages'], list):
        return False
    if entry['type'] not in {'entry', 'reference'}:
        return False
    if entry['type'] == 'reference' and 'see' not in entry:
        return False
    return True

def validate_and_fix_entries(entries, current_page, filename):
    """Validate and fix page numbers in index entries."""
    valid_entries = []
    for entry in entries:
        # Validate JSON structure
        if not validate_json_structure(entry):
            logging.warning(f"File {filename}: Invalid entry structure: {entry}")
            continue
            
        # Check if the page number is correct
        if entry['pages'] != [current_page]:
            logging.warning(f"File {filename}: Entry '{entry['term']}' has incorrect page number {entry['pages']} (should be [{current_page}])")
        entry['pages'] = [current_page]
        valid_entries.append(entry)
    return valid_entries

def make_api_call_with_retry(prompt, content, max_retries=3, base_delay=1):
    """Make API call with retry logic."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n{content}"
                    }
                ],
                max_tokens=800,
                temperature=0.1
            )
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            delay = base_delay * (2 ** attempt)  # Exponential backoff
            logging.warning(f"API call failed, retrying in {delay} seconds... Error: {e}")
            time.sleep(delay)

def load_existing_index():
    """Load existing index if it exists and return processed page numbers."""
    index_file = Path('intermediate_files') / 'index.json'
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            existing_index = json.load(f)
            # Get set of already processed pages
            processed_pages = {entry['pages'][0] for entry in existing_index}
            logging.info(f"Loaded existing index with {len(existing_index)} entries covering {len(processed_pages)} pages")
            return existing_index, processed_pages
    return [], set()

def setup_folders():
    """Create necessary folders for the index generator."""
    folders = ['intermediate_files', 'intermediate_files/book_pages', 'intermediate_files/backups']
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

def get_paths():
    """Get paths for input and output files."""
    return {
        'intermediate': Path('intermediate_files'),
        'book_pages': Path('intermediate_files') / 'book_pages',
        'backups': Path('intermediate_files') / 'backups'
    }

def generate_index():
    """Generate index from parsed data using GPT-4o."""
    # Setup folders
    setup_folders()
    paths = get_paths()

    # Directory containing the split pages
    book_pages_path = Path('intermediate_files') / 'book_pages'

    # Prepare the prompt for GPT-4o
    prompt = (
        "You are an expert in indexing academic books, following the Oxford University Press (OUP) guidelines. "
        "Your task is to generate a concise and well-structured index from the provided page content. "
        "Focus on key terms that readers are most likely to look up, ensuring the index includes significant names, places, and themes/concepts. "
        "Avoid including names and terms mentioned only in passing, and limit the number of page locators per entry to 6-8. "
        "Use cross-references where appropriate, and ensure the index is formatted with main entries and sub-entries. "
        "Do not include frontmatter, endmatter, or chapter titles unless there is significant discussion not covered in the main text. "
        "Importantly, exclude any content that appears to be footnotes. Footnotes are typically self-contained sentences that start with a number and interrupt the flow of the writing.\n\n"
        "Generate entries only for the content on this specific page. Do not reference other pages.\n\n"
        "Example output format:\n"
        "[\n"
        "  {\n"
        "    \"term\": \"Key Concept\",\n"
        "    \"type\": \"entry\",\n"
        "    \"pages\": [PAGE_NUMBER],\n"
        "    \"original_term\": \"Key Concept\"\n"
        "  },\n"
        "  {\n"
        "    \"term\": \"Another Term\",\n"
        "    \"type\": \"reference\",\n"
        "    \"pages\": [PAGE_NUMBER],\n"
        "    \"original_term\": \"Another Term\",\n"
        "    \"see\": \"Key Concept\"\n"
        "  }\n"
        "]\n"
    )

    # Load existing index and processed pages
    index, processed_pages = load_existing_index()

    # Get sorted list of page files
    page_files = sorted(book_pages_path.glob("page_*.txt"), 
                       key=lambda x: int(x.stem.split('_')[1]))
    
    # Filter out already processed pages
    remaining_files = [f for f in page_files 
                      if int(f.stem.split('_')[1]) not in processed_pages]
    
    if not remaining_files:
        print("All pages have been processed already!")
        return
    
    # Log the total number of pages to process
    total_pages = len(remaining_files)
    logging.info(f"Starting to process {total_pages} remaining pages")

    # Create backup directory
    backup_dir = Path('intermediate_files') / 'backups'
    backup_dir.mkdir(exist_ok=True)

    # Initialize failed_pages list
    failed_pages = []

    # Process pages
    with tqdm(total=total_pages, desc="Generating index", unit="page") as progress_bar:
        for i, page_file in enumerate(remaining_files):
            filename = page_file.name
            page_number = int(page_file.stem.split('_')[1])
            logging.info(f"Processing file: {filename} (page {page_number})")
            
            progress_bar.set_description(f"Processing {filename}")

            try:
                with open(page_file, 'r', encoding='utf-8') as f:
                    page_content = f.read()

                # Replace PAGE_NUMBER in prompt with actual page number
                current_prompt = prompt.replace('PAGE_NUMBER', str(page_number))

                # Make API call with retry logic
                response = make_api_call_with_retry(current_prompt, page_content)
                raw_content = response.choices[0].message.content
                logging.info(f"Raw response for {filename}: {raw_content}")

                cleaned_content = clean_response_content(raw_content)

                if cleaned_content:
                    try:
                        index_entries = json.loads(cleaned_content.strip())
                        validated_entries = validate_and_fix_entries(index_entries, page_number, filename)
                        index.extend(validated_entries)
                        logging.info(f"Successfully processed {filename}")
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON decode error for {filename}: {e}")
                        failed_pages.append((filename, page_number))
                else:
                    logging.warning(f"No valid response for {filename}")
                    failed_pages.append((filename, page_number))

            except Exception as e:
                logging.error(f"Error processing {filename}: {e}")
                failed_pages.append((filename, page_number))
            
            progress_bar.update(1)

            # Save backup every 20 pages
            if i > 0 and i % 20 == 0:
                save_backup(index, backup_dir)

    # Retry failed pages if any exist
    if failed_pages:
        logging.info(f"Retrying {len(failed_pages)} failed pages...")
        still_failed = []
        
        with tqdm(total=len(failed_pages), desc="Retrying failed pages", unit="page") as retry_bar:
            for filename, page_number in failed_pages:
                retry_bar.set_description(f"Retrying {filename}")
                
                try:
                    with open(book_pages_path / filename, 'r', encoding='utf-8') as f:
                        page_content = f.read()

                    current_prompt = prompt.replace('PAGE_NUMBER', str(page_number))
                    response = make_api_call_with_retry(current_prompt, page_content)
                    raw_content = response.choices[0].message.content
                    logging.info(f"Retry response for {filename}: {raw_content}")

                    cleaned_content = clean_response_content(raw_content)
                    if cleaned_content:
                        try:
                            index_entries = json.loads(cleaned_content.strip())
                            validated_entries = validate_and_fix_entries(index_entries, page_number, filename)
                            index.extend(validated_entries)
                            logging.info(f"Successfully processed {filename} on retry")
                        except json.JSONDecodeError as e:
                            logging.error(f"JSON decode error for {filename} on retry: {e}")
                            still_failed.append((filename, page_number))
                    else:
                        still_failed.append((filename, page_number))

                except Exception as e:
                    logging.error(f"Error processing {filename} on retry: {e}")
                    still_failed.append((filename, page_number))
                
                retry_bar.update(1)

        if still_failed:
            logging.warning(f"{len(still_failed)} pages still failed after retry")
            with open(Path('intermediate_files') / 'failed_pages.json', 'w', encoding='utf-8') as f:
                json.dump(still_failed, f, ensure_ascii=False, indent=2)

    # Before saving final index, merge duplicates and validate
    logging.info("Merging duplicate entries...")
    index = merge_duplicate_entries(index)

    # Final validation pass
    logging.info("Performing final validation...")
    final_index = []
    for entry in index:
        if validate_entry_content(entry):
            final_index.append(entry)
        else:
            logging.warning(f"Removed invalid entry during final validation: {entry}")

    # Sort the final index by page number
    final_index.sort(key=lambda x: x['pages'][0])

    # Save the final sorted index
    output_file = Path('intermediate_files') / 'index.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_index, f, ensure_ascii=False, indent=2)

    success_message = f"Index generated and saved to {output_file}"
    print(success_message)
    logging.info(success_message)

def merge_duplicate_entries(entries):
    """Merge entries with the same term and type."""
    merged = {}
    for entry in entries:
        key = (entry['term'], entry['type'])
        if key in merged:
            # Merge pages lists
            merged[key]['pages'] = sorted(list(set(
                merged[key]['pages'] + entry['pages']
            )))
            logging.info(f"Merged duplicate entry '{entry['term']}' from pages {entry['pages']}")
        else:
            merged[key] = entry
    return list(merged.values())

def validate_entry_content(entry):
    """Enhanced validation for entry content."""
    # Check for empty or whitespace-only terms
    if not entry['term'].strip():
        return False
    
    # Check for terms that are too long (probably errors)
    if len(entry['term']) > 200:
        return False
    
    # Check for common formatting issues
    if entry['term'].startswith(('(', '[', '{', '"', "'")):
        return False
        
    # Check for obviously wrong page numbers
    if any(p < 1 or p > 1000 for p in entry['pages']):
        return False
        
    return True

def save_backup(index, backup_dir):
    """Save a backup of the current index."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f'index_backup_{timestamp}.json'
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    # Keep only the last 5 backups
    backups = sorted(backup_dir.glob('index_backup_*.json'))
    if len(backups) > 5:
        for old_backup in backups[:-5]:
            old_backup.unlink()

if __name__ == "__main__":
    setup_logging()
    generate_index() 