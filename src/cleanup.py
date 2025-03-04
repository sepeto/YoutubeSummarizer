import os
import shutil
from datetime import datetime
import argparse

def cleanup_output(output_dir='output', backup_dir='output_old'):
    """
    Move old output files to a timestamped backup directory
    """
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{backup_dir}_{timestamp}"
    
    # Create backup directory if it doesn't exist
    os.makedirs(backup_path, exist_ok=True)
    
    # Move all files from output to backup
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            s = os.path.join(output_dir, item)
            d = os.path.join(backup_path, item)
            if os.path.isfile(s) or os.path.isdir(s):
                shutil.move(s, d)
        print(f"Files moved to {backup_path}")
    else:
        print(f"Output directory {output_dir} does not exist")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Clean up old output files')
    parser.add_argument('--output-dir', default='output', help='Output directory to clean')
    parser.add_argument('--backup-dir', default='output_old', help='Backup directory prefix')
    
    args = parser.parse_args()
    cleanup_output(args.output_dir, args.backup_dir) 