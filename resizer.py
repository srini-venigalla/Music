import subprocess
import sys
import os

def process_video(input_file, mode, x="0", y="(ih-oh)/2"):
    file_name, file_ext = os.path.splitext(input_file)
    output_file = f"{file_name}_169_{mode}_x{x}_y{y}{file_ext}"

    # Mode logic
    # Note: 'x' and 'y' only apply to 'crop' mode in this setup
    modes = {
        "crop": f"crop=iw:iw*9/16:{x}:{y}",
        "pad": "pad=ih*16/9:ih:(ow-iw)/2:(oh-ih)/2",
        "blur": "split[v1][v2];[v1]scale=ih*16/9:-1,boxblur=20:10[bg];[v2]scale=-1:ih[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,crop=ih*16/9:ih"
    }

    if mode not in modes:
        print(f"Error: Mode '{mode}' not recognized.")
        return

    cmd = [
        'ffmpeg', '-i', input_file,
        '-vf', modes[mode],
        '-c:a', 'copy',
        '-y',
        output_file
    ]

    try:
        print(f"--- Executing: {mode.upper()} (X:{x}, Y:{y}) ---")
        subprocess.run(cmd, check=True)
        print(f"Success! Saved: {output_file}")
    except subprocess.CalledProcessError:
        print("Error: FFmpeg failed. Check your coordinates.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python resizer.py <file> <mode> <x_offset> <y_offset>")
        print("Example: python resizer.py vid.mp4 crop 0 0  (Top Crop)")
        print("Example: python resizer.py vid.mp4 crop 0 100 (Shift down 100px)")
    else:
        # Default X to 0 and Y to center if not provided
        mode_arg = sys.argv[2].lower()
        x_arg = sys.argv[3] if len(sys.argv) > 3 else "0"
        y_arg = sys.argv[4] if len(sys.argv) > 4 else "(ih-oh)/2"
        
        process_video(sys.argv[1], mode_arg, x_arg, y_arg)