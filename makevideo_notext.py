import subprocess
import os
import sys
import shlex
import re
import tempfile
import argparse

# --- CONSTANTS ---
TARGET_RES = "1280:720"
FPS = 24


def get_duration(filename, start_time=None, end_time=None):
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".webp"]:
        try:
            return float(start_time) if start_time else 5.0
        except:
            return 5.0
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(filename)}"
    try:
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        total_dur = float(output)

        def to_sec(t):
            if not t:
                return None
            parts = str(t).split(":")
            return sum(float(x) * 60**i for i, x in enumerate(reversed(parts)))

        s = to_sec(start_time) or 0.0
        e = to_sec(end_time) or total_dur
        return e - s
    except:
        return 5.0


def parse_line(line):
    line = line.strip()
    if not line or line.startswith("--"):
        return None, None, None
    line = re.sub(r"--.*", "", line).strip()
    match = re.search(
        r"^(.*?)\s+(\d{2}:\d{2}:\d{2}(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s+(\d{2}:\d{2}:\d{2}(?:\.\d+)?|\d+(?:\.\d+)?))?$",
        line,
    )
    if match:
        return match.group(1).strip(), match.group(2), match.group(3)
    return line, None, None


def run_ffmpeg_with_cb(cmd, desc, debug=False):
    """
    Monitors for runaway FPS and handles log visibility.
    Prints the filename clearly in the terminal since FFmpeg lacks drawtext.
    """
    # High-visibility header in terminal
    print(f"\n▶️  NOW PROCESSING: {desc}")
    if debug:
        print(f"COMMAND: {cmd}\n")

    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    frame_count = 0
    for line in process.stdout:
        if debug:
            sys.stdout.write(line)
            sys.stdout.flush()

        # Circuit Breaker Logic
        fps_match = re.search(r"fps=\s*(\d+)", line)
        if fps_match:
            current_fps = int(fps_match.group(1))
            frame_match = re.search(r"frame=\s*(\d+)", line)
            if frame_match:
                frame_count = int(frame_match.group(1))

            if current_fps > 450 and frame_count > 50:
                process.terminate()
                print(f"\n🛑 CIRCUIT BREAKER: {desc} hit {current_fps} fps. Aborting.")
                sys.exit(1)

        if not debug and "frame=" in line:
            # Clean single-line progress
            sys.stdout.write(f"\r   {line.strip()[:60]}")
            sys.stdout.flush()

    process.wait()
    if process.returncode != 0:
        print(f"\n❌ FAILED: FFmpeg error on {desc}")
        sys.exit(1)


def process_video():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--debug", action="store_true", help="Show full FFmpeg logs")
    args = parser.parse_args()

    base_name = os.path.splitext(args.input)[0]
    final_output = args.output if args.output else f"{base_name}_video.mp4"
    audio_bg = f"{base_name}.mp3"

    temp_dir = tempfile.mkdtemp()
    to_process = []
    with open(args.input, "r") as f:
        for line in f:
            fname, start, end = parse_line(line)
            if fname and os.path.exists(fname):
                to_process.append({"file": fname, "start": start, "end": end})

    processed_ts_files = []
    total = len(to_process)
    print(f"🚀 Render Pipeline | {total} clips | FFmpeg 8.x Optimized")

    for i, cfg in enumerate(to_process):
        filename = cfg["file"]
        short_name = os.path.basename(filename)
        is_img = os.path.splitext(filename)[1].lower() in [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        ]
        raw_dur = get_duration(filename, cfg["start"], cfg["end"])
        out_ts = os.path.join(temp_dir, f"part_{i:04d}.ts")

        # Basic filter chain (No drawtext)
        vf = f"scale={TARGET_RES}:force_original_aspect_ratio=decrease,pad={TARGET_RES}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"

        if is_img:
            # Fix for FFmpeg 8 image runaway
            input_args = (
                f"-loop 1 -t {raw_dur} -framerate {FPS} -i {shlex.quote(filename)}"
            )
        else:
            ss = f"-ss {cfg['start']}" if cfg["start"] else ""
            t_val = (
                f"-t {cfg['end']}"
                if cfg["end"] and ":" not in cfg["end"]
                else (f"-to {cfg['end']}" if cfg["end"] else "")
            )
            input_args = f"-r {FPS} {ss} {t_val} -i {shlex.quote(filename)}"

        cmd = f'ffmpeg -y -fflags +genpts {input_args} -vf "{vf}" -r {FPS} -c:v libx264 -preset superfast -pix_fmt yuv420p -f mpegts {out_ts}'

        run_ffmpeg_with_cb(cmd, f"[{i + 1}/{total}] {short_name}", args.debug)
        processed_ts_files.append(out_ts)

    # Stitching & Final Mix
    concat_file = os.path.join(temp_dir, "concat.txt")
    interim_video = os.path.join(temp_dir, "interim.mp4")
    with open(concat_file, "w") as f:
        for p in processed_ts_files:
            f.write(f"file '{p}'\n")

    print(f"\n🔗 Stitching chunks...")
    subprocess.run(
        f"ffmpeg -y -loglevel error -f concat -safe 0 -i {concat_file} -c:v libx264 -preset superfast -pix_fmt yuv420p {interim_video}",
        shell=True,
    )

    if os.path.exists(audio_bg):
        print(f"🎵 Mixing audio: {audio_bg}")
        subprocess.run(
            f"ffmpeg -y -loglevel error -i {interim_video} -i {shlex.quote(audio_bg)} -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest {final_output}",
            shell=True,
        )
    else:
        if os.path.exists(final_output):
            os.remove(final_output)
        os.rename(interim_video, final_output)

    print(f"✅ Created {final_output}")


if __name__ == "__main__":
    process_video()
