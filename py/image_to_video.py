import subprocess
import sys
import os

def create_loop_video():
    # Parse arguments from CLI: key=value
    args = {}
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            args[k] = v

    image = args.get("image")
    output = args.get("output", "hold_video.mp4")
    duration = args.get("duration", "5")  # Default 5 seconds
    fps = args.get("fps", "30")           # Default 30 fps

    if not image:
        print("Usage: python3 image_to_video.py image='input.png' output='out.mp4' duration=10")
        return

    if not os.path.exists(image):
        print(f"Error: Image '{image}' not found.")
        return

    # FFmpeg Command
    # -loop 1: Loop the single image
    # -t: Limit the duration
    # -vf scale: Ensures width/height are divisible by 2 (required for yuv420p)
    cmd = [
        "ffmpeg", "-y",             # -y overwrites output if it exists
        "-loop", "1", 
        "-i", image, 
        "-c:v", "libx264", 
        "-t", duration, 
        "-r", fps, 
        "-pix_fmt", "yuv420p", 
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", 
        output
    ]

    try:
        print(f"Generating {duration}s video from {image}...")
        subprocess.run(cmd, check=True)
        print(f"Success! Created: {output}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
    except FileNotFoundError:
        print("Error: FFmpeg is not installed or not in your PATH.")

if __name__ == "__main__":
    create_loop_video()