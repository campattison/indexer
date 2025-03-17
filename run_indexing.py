import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_prerequisites():
    """Check if all required files and environment variables are present"""
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found. Please set up your API key in .env file")
        return False
        
    if not Path("word_list.txt").exists():
        print("Error: word_list.txt not found. Please create it with your index terms")
        return False
        
    return True

def run_workflow(pdf_path):
    """Run the complete indexing workflow"""
    try:
        # 1. PDF Splitting
        print("\n=== Stage 1: Splitting PDF ===")
        os.system(f"python pdf_splitter.py {"ema_book.pdf"}")
        
        # 2. Index Generation
        print("\n=== Stage 2: Generating Index ===")
        os.system("python index_generator.py")
        
        # 3. Index Validation
        print("\n=== Stage 3: Validating Index ===")
        os.system("python validate_index.py")
        
        # 4. Index Correction
        print("\n=== Stage 4: Correcting Index ===")
        os.system("python index_corrector.py")
        
        print("\n=== Workflow Complete! ===")
        print("Check the following files for results:")
        print("- book_index_corrected.txt: Your final index")
        print("- index_corrections_summary.txt: Summary of changes made")
        print("- validation_summary.txt: Validation details")
        
    except Exception as e:
        print(f"\nError: Workflow failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_indexing.py your_book.pdf")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"Error: PDF file '{pdf_path}' not found")
        sys.exit(1)
        
    if check_prerequisites():
        run_workflow(pdf_path) 