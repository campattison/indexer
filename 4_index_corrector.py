import re
import json
import sys
import os
from pathlib import Path

# Add file path setup at the top
SCRIPT_DIR = Path(__file__).parent
JSON_DIR = SCRIPT_DIR / "json_files"
INPUT_INDEX = SCRIPT_DIR / "book_index.txt"
VALIDATION_SUMMARY = SCRIPT_DIR / "validation_summary.txt"
OUTPUT_INDEX = SCRIPT_DIR / "book_index_modified.txt"

# Create JSON directory if it doesn't exist
JSON_DIR.mkdir(exist_ok=True)

def normalize_term(term):
    """Normalize a term for consistent comparison."""
    return term.strip().lower()

def convert_index_to_json(book_index_path):
    """Convert the book index to JSON format using the improved parser."""
    print("Converting book index to JSON...")
    
    entries = []
    skipped_lines = []
    line_count = 0
    entry_count = 0
    
    with open(book_index_path, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file]
    
    print(f"Total lines in file: {len(lines)}")
    
    # This will store our final format
    index_entries = {}
    
    for line in lines:
        line_count += 1
        if not line:
            continue
            
        if ':' not in line:
            skipped_lines.append({"line": line, "reason": "no colon separator"})
            continue
        
        try:
            parts = line.split(':', 1)
            term = parts[0].strip()
            rest_of_line = parts[1].strip()
            
            original_term = term
            norm_term = normalize_term(term)
            
            # Handle cross-references
            if 'see' in rest_of_line.lower():
                parent_term = rest_of_line.split('see')[1].strip()
                # Extract page numbers from the parent term
                page_numbers = [int(num.strip()) for num in re.findall(r'\d+', parent_term)]
                # Remove page numbers in parentheses from the parent term
                parent_term = re.sub(r'\s*\([^)]+\)', '', parent_term).strip()
                index_entries[norm_term] = {
                    "type": "reference",
                    "see": parent_term,
                    "pages": sorted(list(set(page_numbers))) if page_numbers else [],
                    "original_term": original_term
                }
                entry_count += 1
                print(f"Added reference: {original_term} -> {parent_term} (pages: {page_numbers})")
            else:
                # Handle regular entries
                page_numbers = [int(num.strip()) for num in re.findall(r'\d+', rest_of_line)]
                if page_numbers:
                    index_entries[norm_term] = {
                        "type": "entry",
                        "pages": sorted(list(set(page_numbers))),
                        "original_term": original_term
                    }
                    entry_count += 1
                    print(f"Added entry: {original_term} -> {page_numbers}")
                else:
                    skipped_lines.append({"line": line, "reason": "no page numbers found"})
                    
        except Exception as e:
            skipped_lines.append({"line": line, "reason": str(e)})
            continue

    print(f"\nInitial index contains {len(index_entries)} entries")
    
    # Save parsed index to JSON
    parsed_index_path = JSON_DIR / "parsed_index.json"
    with open(parsed_index_path, 'w', encoding='utf-8') as f:
        json.dump(index_entries, f, indent=2, ensure_ascii=False)
    print(f"Saved parsed index to {parsed_index_path}")
    
    return index_entries

def extract_false_entries(validation_summary_path):
    """Extract false entries from validation summary and convert to structured format."""
    print("\nExtracting false entries...")
    
    false_entries = []
    with open(validation_summary_path, 'r') as file:
        content = file.read()
        
        # Find the False Entries section
        false_section_match = re.search(r'False Entries:\n(.*?)(?=\n\n\w+|\Z)', content, re.DOTALL)
        if false_section_match:
            false_section = false_section_match.group(1)
            print("Found False Entries section")
            
            # Extract entries with format: "- Term (page X):"
            entries = re.finditer(r'- ([^(]+)\(page (\d+)\):', false_section)
            
            # Convert to structured format
            for entry in entries:
                term = entry.group(1).strip()
                page = int(entry.group(2))
                false_entries.append({
                    "term": term,
                    "page": page
                })
    
    print(f"Extracted {len(false_entries)} false entries")
    
    # Save to JSON file
    false_entries_path = JSON_DIR / "false_entries.json"
    with open(false_entries_path, 'w') as f:
        json.dump(false_entries, f, indent=2)
    print(f"Saved false entries to {false_entries_path}")
    
    return false_entries

def remove_false_entries(index_entries, false_entries):
    """Remove all false entries from the index."""
    print("\nRemoving false entries from index...")
    
    # Create a copy of the dictionary to avoid modification while iterating
    modified_entries = index_entries.copy()
    modifications = 0
    
    print(f"Starting with {len(modified_entries)} entries")
    print("\nProcessing false entries:")
    
    for false_entry in false_entries:
        term = false_entry["term"]
        page = false_entry["page"]
        
        # Normalize the term for comparison
        norm_term = normalize_term(term)
        
        print(f"\nChecking false entry: '{term}' (page {page})")
        
        if norm_term in modified_entries:
            entry = modified_entries[norm_term]
            if entry["type"] == "entry":
                if page in entry["pages"]:
                    # Only remove the specific page
                    entry["pages"].remove(page)
                    modifications += 1
                    print(f"Removed page {page} from '{entry['original_term']}' - remaining pages: {entry['pages']}")
                    
                    # Only remove the entire entry if no pages are left
                    if not entry["pages"]:
                        del modified_entries[norm_term]
                        print(f"Removed empty entry '{entry['original_term']}'")
                else:
                    print(f"Page {page} not found in entry '{entry['original_term']}'")
            else:
                print(f"Entry '{entry['original_term']}' is a reference, not modifying")
        else:
            print(f"Term '{term}' not found in index")
    
    print(f"\nMade {modifications} page removals")
    print(f"Final index contains {len(modified_entries)} entries")
    
    # Save modified index to JSON
    modified_index_path = JSON_DIR / "modified_index.json"
    with open(modified_index_path, 'w', encoding='utf-8') as f:
        json.dump(modified_entries, f, indent=2, ensure_ascii=False)
    print(f"Saved modified index to {modified_index_path}")
    
    return modified_entries

def convert_json_to_index(index_entries, output_path):
    """Convert JSON index back to text format."""
    print("\nConverting JSON index back to text format...")
    
    # Sort entries alphabetically using the original terms
    sorted_terms = sorted(index_entries.keys(), 
                         key=lambda k: normalize_term(index_entries[k]["original_term"]))
    
    # Count entries by type for validation
    reference_count = sum(1 for entry in index_entries.values() if entry["type"] == "reference")
    regular_count = sum(1 for entry in index_entries.values() if entry["type"] == "entry")
    
    print(f"Writing {len(sorted_terms)} total entries:")
    print(f"- {regular_count} regular entries")
    print(f"- {reference_count} reference entries")
    
    with open(output_path, 'w', encoding='utf-8') as file:
        for norm_term in sorted_terms:
            entry = index_entries[norm_term]
            try:
                original_term = entry["original_term"]
                
                if entry["type"] == "reference":
                    if entry.get("pages"):
                        # Just add the page numbers once
                        pages_str = f" ({', '.join(str(p) for p in sorted(entry['pages']))})"
                        line = f"{original_term}: see {entry['see']}{pages_str}\n"
                    else:
                        line = f"{original_term}: see {entry['see']}\n"
                    print(f"Writing reference: {original_term} -> {entry['see']} (pages: {entry.get('pages', [])})")
                elif entry["type"] == "entry":
                    pages = sorted(entry["pages"])
                    pages_str = ', '.join(str(p) for p in pages)
                    line = f"{original_term}: {pages_str}\n"
                    print(f"Writing entry: {original_term} -> {pages}")
                else:
                    print(f"Warning: Unknown entry type for {original_term}: {entry}")
                    continue
                    
                file.write(line)
            except Exception as e:
                print(f"Error writing entry {norm_term}: {str(e)}")
                print(f"Entry data: {entry}")
    
    # Verify the output
    with open(output_path, 'r', encoding='utf-8') as file:
        written_lines = [line for line in file if line.strip()]
    
    print(f"\nVerification:")
    print(f"- Expected entries: {len(sorted_terms)}")
    print(f"- Written entries: {len(written_lines)}")
    
    if len(written_lines) != len(sorted_terms):
        print("WARNING: Mismatch between expected and written entries!")
        
    # Save a conversion report
    conversion_report = {
        "input_entries": len(index_entries),
        "written_entries": len(written_lines),
        "regular_entries": regular_count,
        "reference_entries": reference_count,
        "sample_entries": {
            "first_10": written_lines[:10],
            "last_10": written_lines[-10:]
        }
    }
    
    print(f"\nWrote modified index to {output_path}")

def process_index(input_index_path, validation_summary_path, output_index_path):
    """Main processing function."""
    # Ensure input files exist
    if not os.path.exists(input_index_path):
        print(f"Error: Input file not found at {input_index_path}")
        return
    
    if not os.path.exists(validation_summary_path):
        print(f"Error: Validation summary not found at {validation_summary_path}")
        return
    
    # Convert book index to JSON
    index_entries = convert_index_to_json(input_index_path)
    
    # Extract false entries
    false_entries = extract_false_entries(validation_summary_path)
    
    if not false_entries:
        print("No false entries found")
        return
    
    # Remove false entries from index
    modified_index = remove_false_entries(index_entries, false_entries)
    
    # Convert back to text format
    convert_json_to_index(modified_index, output_index_path)

if __name__ == "__main__":
    # Check if required files exist
    if not INPUT_INDEX.exists():
        print(f"Error: Input index file not found at {INPUT_INDEX}")
        sys.exit(1)
    
    if not VALIDATION_SUMMARY.exists():
        print(f"Error: Validation summary file not found at {VALIDATION_SUMMARY}")
        sys.exit(1)
    
    print(f"Processing index correction:")
    print(f"Input file: {INPUT_INDEX}")
    print(f"Validation file: {VALIDATION_SUMMARY}")
    print(f"Output will be written to: {OUTPUT_INDEX}")
    
    process_index(str(INPUT_INDEX), str(VALIDATION_SUMMARY), str(OUTPUT_INDEX))
