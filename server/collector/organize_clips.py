
import os
import json
import shutil

def get_sign_name_from_resource_path(resource_path):
    """Extracts the sign name from the resourcePath."""
    if not resource_path:
        return None
    basename = os.path.basename(resource_path)
    sign_name, _ = os.path.splitext(basename)
    return sign_name

def find_clip_file(clip_summary, all_clips):
    """Finds the corresponding clip file in the clip_dump directory."""
    base_filename = os.path.splitext(clip_summary['filename'])[0]
    start_s = clip_summary.get('start_s')

    if start_s is None:
        return None

    best_match = None
    min_diff = float('inf')

    for clip_file in all_clips:
        if clip_file.startswith(base_filename) and '_clip_' in clip_file:
            try:
                time_part = clip_file.split('_clip_')[1]
                file_start_s = float(time_part.split('_')[0])
                
                diff = abs(file_start_s - start_s)
                if diff < min_diff:
                    min_diff = diff
                    best_match = clip_file
            except (IndexError, ValueError):
                continue
    
    if min_diff < 1.0: # Match if within 1 second
        return best_match
    else:
        return None

def main():
    """Organizes clips into a review directory structure."""
    CLIP_DUMP_DIR = 'clip_dump'
    REVIEW_DIR = 'ReviewVideos'
    METADATA_FILE = 'metadata_dump.json'

    if not os.path.exists(CLIP_DUMP_DIR):
        print(f"Error: Directory '{CLIP_DUMP_DIR}' not found.")
        return

    if not os.path.exists(METADATA_FILE):
        print(f"Error: Metadata file '{METADATA_FILE}' not found.")
        return

    os.makedirs(REVIEW_DIR, exist_ok=True)

    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    all_clip_files = os.listdir(CLIP_DUMP_DIR)
    
    sign_videos = {}

    for clip in metadata.get('clips', []):
        summary = clip.get('summary', {})
        if summary.get('valid'):
            full_data = clip.get('full', {}).get('data', {})
            prompt_data = full_data.get('promptData', {})
            resource_path = prompt_data.get('resourcePath')

            if not resource_path:
                continue

            sign_name = get_sign_name_from_resource_path(resource_path)
            if not sign_name:
                continue
            
            clip_filename = find_clip_file(summary, all_clip_files)

            if clip_filename:
                if sign_name not in sign_videos:
                    sign_videos[sign_name] = []
                
                source_path = os.path.join(CLIP_DUMP_DIR, clip_filename)
                sign_videos[sign_name].append(source_path)

    batch_size = 10 # max signs per batch
    batch_num = 1 # batch number counter
    sign_count = 0
    batch_dir = None
    
    sorted_sign_names = sorted(sign_videos.keys())

    for sign_name in sorted_sign_names:
        video_paths = sign_videos[sign_name]
        if not video_paths:
            continue

        if sign_count % batch_size == 0:
            batch_dir = os.path.join(REVIEW_DIR, f'Batch {batch_num}')
            os.makedirs(batch_dir, exist_ok=True)
            batch_num += 1
        
        sign_dir = os.path.join(batch_dir, sign_name)
        os.makedirs(sign_dir, exist_ok=True)
        
        for video_path in video_paths:
            dest_filename = os.path.basename(video_path)
            dest_path = os.path.join(sign_dir, dest_filename)
            print(f"Moving {video_path} to {dest_path}")
            shutil.move(video_path, dest_path)
            
        sign_count += 1

if __name__ == '__main__':
    main()
