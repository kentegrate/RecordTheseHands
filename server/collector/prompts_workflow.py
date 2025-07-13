import os
import sys
import subprocess
import re

def run_phrases_to_prompts(prefix, path_to_prompt_txt):
    try:
        # Run the provided script and capture its output
        result = subprocess.run(
            ['python', 'phrases_to_prompts.py', prefix, path_to_prompt_txt],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Output the stdout and stderr for debugging purpose
        print(f"stdout:\n{result.stdout}")
        print(f"stderr:\n{result.stderr}")

        # Extract JSON file path from the script output
        match = re.search(r'prompts written to (.+\.json)', result.stdout)
        if match:
            json_filepath = match.group(1).strip()
            return json_filepath
        else:
            raise RuntimeError("Failed to find JSON filepath in script output.")
    
    except subprocess.CalledProcessError as error:
        print(f"Error running phrases_to_prompts.py: {error}")
        sys.exit(1)

def upload_file_to_gcs(local_filepath, gcs_bucket_path):
    try:
        # Use gsutil to upload the file
        print(gcs_bucket_path)
        subprocess.run(['gsutil', 'cp', '-L log.txt', local_filepath, gcs_bucket_path], check=True)

        print(f"Uploaded {local_filepath} to {gcs_bucket_path}")
    except subprocess.CalledProcessError as error:
        print(f"Failed to upload file: {error}")
        sys.exit(1)

def create_directive(json_filepath):
    try:
        json_filename = os.path.basename(json_filepath)
        subprocess.run(['python', 'create_directive.py', 'admin3', 'downloadTutorialPrompts', f'prompts/{json_filename}'], check=True)
        print(f"Directive created for {json_filename}")
    except subprocess.CalledProcessError as error:
        print(f"Failed to create directive: {error}")
        sys.exit(1)

def create_batch_directive(json_filepath, username_prefix, n_participants, mode='downloadTutorialPrompts', start_idx=0):
    for i in range(start_idx, n_participants):
        try:
            json_filename = os.path.basename(json_filepath)
            subprocess.run(['python', 'create_directive.py', f'{username_prefix}{i:03d}', mode, f'prompts/{json_filename}'], check=True)
            print(f"Directive created for {json_filename}")
        except subprocess.CalledProcessError as error:
            print(f"Failed to create directive: {error}")
            sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py [PREFIX] [path_to_prompt_txt]")
        sys.exit(1)

    prefix = sys.argv[1]
    path_to_prompt_txt = sys.argv[2]

    # Step 1: Run the existing phrases_to_prompts.py script
    json_filepath = run_phrases_to_prompts(prefix, path_to_prompt_txt)

    # Step 2: Upload the JSON file to GCS
    gcs_bucket_path = 'gs://jsl-collection-1.appspot.com/prompts'
    upload_file_to_gcs(json_filepath, gcs_bucket_path)

    # Step 3: Add a directive for the uploaded JSON file
    create_batch_directive(json_filepath, "jsl0712s", 16, 'downloadPrompts', 15)
#    create_batch_directive(json_filepath, "jsl0712s", 16, 'downloadTutorialPrompts', 15)

if __name__ == "__main__":
    main()