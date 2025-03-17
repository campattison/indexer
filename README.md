# Automated Book Indexing System

A comprehensive system for generating, validating, and correcting book indexes using AI.

## Quick Start for Non-Technical Users

The easiest way to use this system is through [Cursor](https://cursor.sh) or [Google Colab](https://colab.research.google.com):

### Using Cursor (Recommended)
1. Download and install [Cursor](https://cursor.sh) - it's a user-friendly code editor designed for AI-assisted development
2. Open Cursor and select "Clone Repository"
3. Enter this repository's URL
4. Follow the "System Workflow" instructions below

### Using Google Colab
1. Visit [Google Colab](https://colab.research.google.com)
2. Create a new notebook
3. Upload all the project files using the file browser on the left
4. Follow the "System Workflow" instructions below, but use the Colab interface to run commands

## Prerequisites

- Python 3.8 or higher
- OpenAI API key (you can get one [here](https://platform.openai.com/api-keys). This will cost money to run (approx. $20 per book).)
- Required Python packages (install using `pip install -r requirements.txt`):
  - openai>=1.0.0
  - PyPDF2>=3.0.0
  - python-dotenv>=1.0.0
  - typing-extensions>=4.0.0
  - requests>=2.0.0
  - tqdm>=4.65.0
  - logging>=0.5.0

To install the required packages, run:
```bash
pip install PyMuPDF
pip install openai
```

### Setting Up Your API Key

There are two ways to set up your OpenAI API key:

1. **Using a .env file (Recommended)**:
   - Copy the provided `.env.example` file to create your own `.env` file:
     ```bash
     cp .env.example .env
     ```
   - Edit the `.env` file and replace `your_openai_api_key_here` with your actual API key
   - The format should be: `OPENAI_API_KEY=sk-your-actual-api-key-here` (no quotes, no spaces around =)
   
   **IMPORTANT SECURITY NOTES:**
   - NEVER commit your `.env` file to version control
   - The `.env` file is already added to `.gitignore` to prevent accidental commits
   - Keep sensitive API keys private and secure
   - Rotate your API keys periodically
   - Consider setting usage limits on your OpenAI account

2. **Using environment variables directly**:
   ```bash
   # Windows (Command Prompt)
   set OPENAI_API_KEY=your-api-key-here

   # Windows (PowerShell)
   $env:OPENAI_API_KEY="your-api-key-here"

   # Linux/MacOS
   export OPENAI_API_KEY="your-api-key-here"
   ```

## System Workflow

The indexing process requires running several scripts in sequence. Here's the step-by-step process:

### 1. PDF Splitting
First, split your PDF into individual pages:
```bash
python pdf_splitter.py your_book.pdf
```
This creates individual text files in the `book_pages` directory.

### 2. Index Generation
Before running this step:
1. Create a `word_list.txt` file with your index terms (one per line)
2. Ensure your OpenAI API key is set up in `.env`

Then run:
```bash
python index_generator.py
```
This creates `book_index.txt` and initial validation data.

### 3. Index Validation
Run the validation script:
```bash
python validate_index.py
```
This generates:
- `validation_results.log`: Detailed validation logs
- `index_validation_report.json`: Structured validation data
- `validation_summary.txt`: Human-readable summary

### 4. Index Correction
Finally, run the correction script:
```bash
python index_corrector.py
```
This produces:
- `book_index_corrected.txt`: The corrected index
- `index_corrections_report.json`: Detailed correction data
- `index_corrections_summary.txt`: Human-readable correction summary
- `index_correction.log`: Process log

## Understanding the Output Files

### Validation Files
The validator checks for:
- False entries (terms not actually in the text)
- Low-confidence entries
- Inconsistent term relationships
- Missing significant terms

### Correction Files
The corrector automatically:
1. Removes false positive entries
2. Handles questionable entries based on confidence scores
3. Fixes inconsistent term relationships
4. Adds missing high-confidence terms

### Review and Quality Control
After completing all steps:
1. Check `index_corrections_summary.txt` for a human-readable list of changes
2. Review entries marked as "Retained for Review" in the confidence issues section
3. Verify any added entries in the original text
4. Use the corrected index in `book_index_corrected.txt`

## Best Practices

1. **Word List Preparation**
   - Include variant forms of terms
   - Use consistent capitalization
   - Include common abbreviations

2. **Validation Review**
   - Always check the validation summary before running corrections
   - Pay special attention to low-confidence entries
   - Verify term relationships

3. **Correction Review**
   - Review all automatic corrections in `index_corrections_summary.txt`
   - Manually verify any entries with confidence scores between 0.5 and 0.8
   - Cross-check added terms against your original word list

4. **Quality Assurance**
   - Keep backups of all generated files
   - Document any manual changes
   - Run validation again after significant corrections

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify your OpenAI API key in the `.env` file
   - Check API key permissions and quota

2. **File Not Found Errors**
   - Ensure all required files are in the correct directories
   - Check file permissions

3. **Validation Errors**
   - Verify the format of your word list
   - Check for special characters in terms
   - Ensure page files are properly formatted

### Getting Help

If you encounter issues:
1. Check the log files in the `logs` directory
2. Review the validation and correction reports
3. Verify your Python environment and dependencies
4. Open an issue in the repository with:
   - Error messages
   - Relevant log contents
   - Steps to reproduce the issue

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with:
   - Clear description of changes
   - Updated tests if applicable
   - Updated documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details. 