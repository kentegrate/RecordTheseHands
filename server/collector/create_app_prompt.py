import os
import glob
import shutil
import subprocess
import sys
from unidecode import unidecode
import unicodedata
import re
from tqdm import tqdm

# Example Usage:
# python create_app_prompt.py path/to/videos jsl-collection-1.appspot.com/resource/folder
#
# What this script does:
# 1. Scans a local directory for .mp4 video files.
# 2. Skips any files with "セッション終了です" (Session Ended) or "休憩時間です" (Break Time) in the name.
# 3. For each video, it creates a "safe" filename by converting all characters to their ASCII equivalents (e.g., 'こんにちは' -> 'konnichiha') and replacing special characters with underscores.
# 4. It copies the video to a temporary location with the new safe name.
# 5. It uploads this temporary file to the specified Google Cloud Storage (GCS) bucket and path using the `gsutil` command-line tool.
# 6. It generates a line for a `prompts.txt` file, which maps the video's location in GCS to text extracted from its original filename.
# 7. After processing all videos, it writes the collected lines into `prompts.txt` in the parent directory of the input folder.

def make_safe_filename(filename):
    """
    Converts a filename into a safe, ASCII-only format.
    - Converts non-ASCII characters (like Kanji) to their closest ASCII representation.
    - Replaces any remaining non-alphanumeric characters with an underscore.
    """
    base_name = os.path.basename(filename)
    # Convert characters to their ASCII representation (e.g., '日本語' -> 'ri ben yu')
    ascii_name = unidecode(base_name)
    # Replace any character that is not a letter, number, or underscore with an underscore.
    safe_name = re.sub(r'[^\w.-]', '_', ascii_name)
    return safe_name

def get_mp4_files(directory_path):
    """
    Gets a list of all .mp4 files from a specified directory.
    """
    if not os.path.isdir(directory_path):
        print(f"Error: Directory not found at '{directory_path}'")
        sys.exit(1)
    return glob.glob(os.path.join(directory_path, '*.mp4'))

def process_files(directory_path, gcp_bucket_path):
    """
    Processes each .mp4 file: renames it for safety, creates a temporary copy,
    uploads it to GCS, and generates a prompt entry.
    """
    mp4_files = get_mp4_files(directory_path)
    prompts = []
    
    # Ensure the GCS path doesn't end with a slash for consistent joining.
    if gcp_bucket_path.endswith("/"):
        gcp_bucket_path = gcp_bucket_path.rstrip("/")

    os.makedirs("safe_names", exist_ok=True)  # Create a directory to store safe names if needed
    for mp4_file in tqdm(mp4_files):
        # Normalize the filename to handle different Unicode encodings, common on macOS.
        normalized_filename = unicodedata.normalize('NFC', mp4_file)
        
        # Skip files that are designated as session end or break markers.
        if "セッション終了です" in normalized_filename or "休憩時間です" in normalized_filename:
            print(f"Skipping file: {os.path.basename(mp4_file)}")
            continue

        print(f"Processing file: {os.path.basename(mp4_file)}")
        safe_filename = make_safe_filename(mp4_file)
        print(f"  -> Safe filename: {safe_filename}")

        # Create a temporary copy with the safe filename to avoid issues with special characters during upload.
        temp_path = os.path.join('safe_names', safe_filename)
        try:
            shutil.copy(mp4_file, temp_path)
        except IOError as e:
            print(f"Error copying file to temporary location: {e}")
            continue # Skip to the next file

        # Prepare the full destination path on Google Cloud Storage.
        gcp_dest_full_url = f"gs://{gcp_bucket_path}/{safe_filename}"
        
        # Construct the relative path for the prompts.txt file.
        # This path starts from the bucket name, not gs://
        bucket_and_folders = gcp_bucket_path.split('/')
        gcp_relative_path = "/".join(bucket_and_folders[1:] + [safe_filename])
        
        # Extract the Japanese text from the original filename.
        # This assumes a format like 'someprefix_テキスト.mp4'
        try:
            jp_txt = os.path.basename(mp4_file).split("_")[1].replace(".mp4", "")
            prompts.append(f"VIDEO {gcp_relative_path} {jp_txt}\n")
        except IndexError:
            print(f"  -> Warning: Could not extract text from filename '{os.path.basename(mp4_file)}'. Skipping prompt generation for this file.")
            continue

        # Upload the temporary file to GCS using the gsutil command.
        try:
            print(f"  -> Uploading to {gcp_dest_full_url}...")
            subprocess.run(
                ['gsutil', 'cp', temp_path, gcp_dest_full_url], 
                check=True, 
                text=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE
            )            
            print(f"  -> Successfully uploaded.")
        except subprocess.CalledProcessError as e:
            print(f"  -> Error uploading {safe_filename}: {e}")
            print(f"  -> GSUtil Stderr: {e.stderr}")

    # Write the collected prompts to a text file in the parent directory.
    if prompts:
        parent_dir = os.path.dirname(directory_path.rstrip('/'))
        prompts_file_path = os.path.join(parent_dir, "prompts.txt")
        try:
            with open(prompts_file_path, "w", encoding='utf-8') as f:
                f.writelines(prompts)
            print(f"\nSuccessfully created prompts file at: {prompts_file_path}")
        except IOError as e:
            print(f"\nError writing prompts file: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <directory-path> <gcp-bucket-and-path>")
        print("Example: python script.py 'path/to/my videos' 'my-gcs-bucket/target_folder'")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    gcp_bucket_path = sys.argv[2]
    
    process_files(directory_path, gcp_bucket_path)
