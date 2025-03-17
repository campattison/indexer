# validate_index.py
# This script validates the index by checking if the terms are significantly discussed in the text.
# It uses OpenAI's GPT-4o model to validate the index.
# The script handles errors and prints helpful messages to the console.
# =====================================
# To use the script, add your API key in the environment or in the script below, and locate the load_files() function changing any of the file paths as needed.
# =====================================

# Now proceed with regular imports
import os
import json
import logging
from pathlib import Path
from openai import OpenAI
import time
from tqdm import tqdm

class AdaptiveRateLimiter:
    """Adaptive rate limiting to prevent API throttling."""
    def __init__(self, initial_delay=1):
        self.delay = initial_delay
        self.last_call = 0
        self.consecutive_failures = 0

    def wait_if_needed(self):
        """Wait if necessary to maintain rate limit."""
        now = time.time()
        time_since_last = now - self.last_call
        if time_since_last < self.delay:
            time.sleep(self.delay - time_since_last)
        self.last_call = time.time()

    def handle_error(self, error_type):
        """Adjust delay based on error type."""
        self.consecutive_failures += 1
        self.delay *= (1.5 ** self.consecutive_failures)
        logging.warning(f"Increased rate limit delay to {self.delay}s")

    def handle_success(self):
        """Gradually reduce delay after successful calls."""
        if self.consecutive_failures > 0:
            self.consecutive_failures = 0
            self.delay = max(1, self.delay * 0.8)

class IndexValidator:
    def __init__(self, test_mode=False, test_limit=10):
        """Initialize the validator with optional test mode."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.rate_limiter = AdaptiveRateLimiter()
        self.test_mode = test_mode
        self.test_limit = test_limit
        self.setup_logging()

    def setup_logging(self):
        """Set up logging configuration."""
        logs_path = Path('intermediate_files')
        os.makedirs(logs_path, exist_ok=True)
        log_file = logs_path / 'validation.log'

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Validation logging setup complete.")

    def load_index(self):
        """Load the index from index.json."""
        index_path = Path('intermediate_files') / 'index.json'
        if not index_path.exists():
            raise FileNotFoundError("index.json not found")
        
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_page_content(self, page_number):
        """Load content for a specific page."""
        page_file = Path('intermediate_files') / 'book_pages' / f'page_{page_number}.txt'
        if not page_file.exists():
            logging.error(f"Page file not found: {page_file}")
            return None
        
        with open(page_file, 'r', encoding='utf-8') as f:
            return f.read()

    def verify_term_occurrence(self, entry, page_content, max_retries=3):
        """Verify if a term is significantly discussed on its page."""
        if not page_content:
            return None

        prompt = (
            "As an expert indexer, evaluate whether this term is significantly discussed in the text. "
            "Consider these specific criteria:\n"
            "1. SIGNIFICANCE:\n"
            "   - Is the term central to the argument or explanation?\n"
            "   - Is it defined, analyzed, or explored in detail?\n"
            "   - Is it used in developing a key point?\n\n"
            "2. EXCLUSION CRITERIA:\n"
            "   - Ignore mentions only in passing\n"
            "   - Ignore mentions only in citations or references\n"
            "   - Ignore mentions only in footnotes\n\n"
            "3. CROSS-REFERENCES (if applicable):\n"
            "   - Is the connection between terms meaningful?\n"
            "   - Would the cross-reference help readers?\n\n"
            "4. CONTEXT:\n"
            "   - Is the term discussed in a substantive way?\n"
            "   - Is there enough context for readers to learn something?\n"
            "   - Would this page reference be valuable to readers?\n\n"
            "Respond with a JSON object containing:\n"
            "{\n"
            '  "is_significant": boolean,\n'
            '  "confidence": float (0.0 to 1.0),\n'
            '  "reasoning": "detailed explanation of decision"\n'
            "}\n\n"
            f"Term to evaluate: {entry['term']}\n"
            f"Entry type: {entry['type']}\n"
            f"Original form: {entry['original_term']}\n"
            f"Text content:\n{page_content}"
        )

        for attempt in range(max_retries):
            try:
                self.rate_limiter.wait_if_needed()
                
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "system",
                        "content": "You are an expert academic indexer following Oxford University Press guidelines."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }],
                    max_tokens=500,
                    temperature=0.1
                )
                
                self.rate_limiter.handle_success()
                return json.loads(response.choices[0].message.content)
                
            except Exception as e:
                self.rate_limiter.handle_error(str(e))
                if attempt == max_retries - 1:
                    logging.error(f"Error validating term '{entry['term']}': {str(e)}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff

    def validate_index(self):
        """Validate the index entries against their page content."""
        # Load the index
        index = self.load_index()
        logging.info(f"Loaded index with {len(index)} entries")

        # Create backup of original index
        backup_path = Path('intermediate_files') / 'index_backup.json'
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        # Track validation results
        validated_entries = []
        removed_entries = []
        validation_errors = []

        # Apply test mode limit if enabled
        if self.test_mode:
            index = [entry for entry in index if any(p <= self.test_limit for p in entry['pages'])]
            logging.info(f"Test mode: processing {len(index)} entries with pages <= {self.test_limit}")

        # Process each entry
        with tqdm(total=len(index), desc="Validating entries", unit="entry") as progress_bar:
            for entry in index:
                entry_pages = entry['pages'].copy()  # Copy to avoid modifying while iterating
                
                for page_number in entry_pages:
                    if self.test_mode and page_number > self.test_limit:
                        continue
                        
                    page_content = self.load_page_content(page_number)
                    if page_content:
                        result = self.verify_term_occurrence(entry, page_content)
                        
                        if result:
                            if result['is_significant'] and result['confidence'] >= 0.7:
                                if entry not in validated_entries:
                                    validated_entries.append(entry)
                            else:
                                removed_entries.append({
                                    'entry': entry,
                                    'page': page_number,
                                    'reason': result['reasoning'],
                                    'confidence': result['confidence']
                                })
                                # Remove this page from the entry's pages
                                if page_number in entry['pages']:
                                    entry['pages'].remove(page_number)
                        else:
                            validation_errors.append({
                                'entry': entry,
                                'page': page_number,
                                'error': 'API validation failed'
                            })
                    
                progress_bar.update(1)

        # Remove entries with no remaining pages
        validated_entries = [entry for entry in validated_entries if entry['pages']]

        # Save validated index
        output_file = Path('intermediate_files') / 'validated_index.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(validated_entries, f, ensure_ascii=False, indent=2)

        # Save comprehensive validation report
        report_file = Path('intermediate_files') / 'validation_report.json'
        report = {
            'statistics': {
                'total_entries': len(index),
                'validated_entries': len(validated_entries),
                'removed_entries': len(removed_entries),
                'validation_errors': len(validation_errors)
            },
            'removed_entries': removed_entries,
            'validation_errors': validation_errors,
            'test_mode': self.test_mode,
            'test_limit': self.test_limit if self.test_mode else None
        }
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logging.info(f"Validation complete. Validated index saved to {output_file}")
        logging.info(f"Validation report saved to {report_file}")

def main():
    """Main entry point with optional test mode."""
    import argparse
    parser = argparse.ArgumentParser(description='Validate index entries.')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--limit', type=int, default=10, help='Page limit for test mode')
    args = parser.parse_args()

    validator = IndexValidator(test_mode=args.test, test_limit=args.limit)
    validator.validate_index()

if __name__ == "__main__":
    main() 