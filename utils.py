import os

def setup_folders():
    """Create folder structure if it doesn't exist."""
    folders = {
        'data': ['input', 'output'],  # For input files and output files
        'logs': ['debug', 'reports'],  # For logs and reports
        'temp': []  # For temporary files
    }
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for folder, subfolders in folders.items():
        folder_path = os.path.join(base_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        for subfolder in subfolders:
            subfolder_path = os.path.join(folder_path, subfolder)
            os.makedirs(subfolder_path, exist_ok=True)
    
    return base_dir

def get_paths():
    """Get all necessary file paths."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    paths = {
        # Input files
        'book_index': os.path.join(base_dir, 'data', 'input', 'book_index.txt'),
        'validation_summary': os.path.join(base_dir, 'data', 'input', 'validation_summary.txt'),
        
        # Output files
        'modified_index': os.path.join(base_dir, 'data', 'output', 'book_index_modified.txt'),
        'parsed_index': os.path.join(base_dir, 'data', 'output', 'parsed_index.json'),
        
        # Debug and report files
        'debug_report': os.path.join(base_dir, 'logs', 'debug', 'index_debug_report.json'),
        'conversion_report': os.path.join(base_dir, 'logs', 'reports', 'conversion_report.json'),
        'false_entries': os.path.join(base_dir, 'logs', 'debug', 'false_entries.json'),
        
        # Temporary files
        'temp_dir': os.path.join(base_dir, 'temp')
    }
    
    return paths 