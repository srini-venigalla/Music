import os
import subprocess
import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="Extract specific frames from a shotlist for Upscayl.")
    parser.add_argument("input", help="Path to the .txt shotlist file")
    parser.add_argument("--debug", action="store_true", help="Print FFmpeg commands for debugging")
    return parser.parse_args()

def extract_frames(shotlist_path, debug=False):
    output_root = "upscayl_input"
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
    
    if not os.path.exists(shotlist_path):
        print(f"Error: File '{shotlist_path}' not found.")
        sys.exit(1)

    if not os.path.exists(output_root):
        os.makedirs(output_root)

    with open(shotlist_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parsing: filename [start] [end/duration]
            parts = line.split()
            filename = parts[0]
            is_image = filename.lower().endswith(image_extensions)
            
            # Unique folder per line
            base_name = os.path.splitext(os.path.basename(filename))[0]
            shot_folder = os.path.join(output_root, f"{base_name}_line{line_num}")
            
            if not os.path.exists(shot_folder):
                os.makedirs(shot_folder)

            cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
            
            if is_image:
                # For static images, we ignore timestamps/duration
                # Upscayl only needs the image once.
                cmd.extend(["-i", filename])
            elif len(parts) >= 2:
                # Video logic: Fast seek -ss BEFORE -i
                start_time = parts[1]
                cmd.extend(["-ss", start_time, "-i", filename])
                
                if len(parts) >= 3:
                    end_val = parts[2]
                    # Duration (-t) vs Timestamp (-to)
                    if ":" not in end_val:
                        cmd.extend(["-t", end_val])
                    else:
                        cmd.extend(["-to", end_val])
            else:
                # Full video extract
                cmd.extend(["-i", filename])

            # Output frames
            cmd.extend(["-q:v", "2", f"{shot_folder}/frame_%04d.jpg"])
            
            if debug:
                print(f"DEBUG: {' '.join(cmd)}")
            else:
                print(f"Processing line {line_num}: {filename}...")

            subprocess.run(cmd)

    print(f"\n✅ Done! Frames extracted to the '{output_root}' directory.")

if __name__ == "__main__":
    args = parse_args()
    extract_frames(args.input, args.debug)
    