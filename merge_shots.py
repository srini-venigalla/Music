import os
import subprocess
import argparse
import sys
import shutil
import re


def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge upscaled PNGs. Auto-detects pattern and FPS."
    )
    parser.add_argument("folder", nargs="?", help="Path to the upscaled folder")
    parser.add_argument("output", nargs="?", help="Target filename (mp4 or png)")
    parser.add_argument("--fps", help="Manual FPS override")
    args = parser.parse_args()
    if not args.folder or not args.output:
        parser.print_help()
        sys.exit()
    return args


def get_fps_from_folder(folder_path, manual_fps=None):
    if manual_fps:
        return manual_fps
    match = re.search(r"(\d+)fps", folder_path)
    return match.group(1) if match else "24"


def detect_pattern(folder_path):
    """Looks at the first PNG to see how it's named."""
    files = sorted([f for f in os.listdir(folder_path) if f.endswith(".png")])
    if not files:
        return None

    first_file = files[0]  # e.g., 'frame_0001.png' or 'frame_0001_upscayl.png'

    # Replace the digits with %04d for FFmpeg
    # This turns 'frame_0001.png' into 'frame_%04d.png'
    pattern = re.sub(r"\d{4}", "%04d", first_file)
    return pattern


def process_upscayled():
    args = parse_args()
    folder_path = args.folder.rstrip("/")

    if not os.path.exists(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        return

    frames = sorted([f for f in os.listdir(folder_path) if f.endswith(".png")])
    if not frames:
        print(f"❌ No PNGs found in {folder_path}")
        return

    if len(frames) == 1:
        shutil.copy2(os.path.join(folder_path, frames[0]), args.output)
        print(f"✅ Success: {args.output} copied.")
        return

    # Detect the pattern (Secret Sauce #2)
    pattern_name = detect_pattern(folder_path)
    input_pattern = os.path.join(folder_path, pattern_name)
    fps = get_fps_from_folder(folder_path, args.fps)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-i",
        input_pattern,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-y",
        args.output,
    ]

    print(f"🎬 Pattern: {pattern_name} | FPS: {fps} -> {args.output}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Created: {args.output}")
    except:
        print(f"❌ FFmpeg failed. Check if {pattern_name} exists in folder.")


if __name__ == "__main__":
    process_upscayled()
