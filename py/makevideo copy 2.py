import subprocess
import os
import sys
import shlex
import re
import tempfile
import argparse

# --- CHANGE HISTORY ---
# 2026-03-22: Fixed crash when using --debug with HOLD by escaping colons in labels.
# 2026-03-22: Added HOLD functionality to freeze video frames at specific timestamps.
# 2026-03-21: Made debug text overlay conditional on --debug flag.
# 2026-01-15: Optimized for M2 Max using h264_videotoolbox and pro-grade bitrate.

# --- PATHS & CONFIG ---
FFMPEG_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
TARGET_RES = "1920:1080"
FPS = 24
BITRATE = "15M"


def get_video_duration(filename):
    cmd = [
        FFPROBE_PATH,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        filename,
    ]
    try:
        out = subprocess.check_output(cmd).decode().strip()
        return float(out)
    except:
        return 0.0


def parse_time(t_str):
    if not t_str:
        return None
    try:
        if ":" not in t_str:
            return float(t_str)
        parts = t_str.split(":")
        return sum(float(x) * 60**i for i, x in enumerate(reversed(parts)))
    except ValueError:
        return None


def run_ffmpeg(cmd, desc, debug=False):
    print(f"\n▶️  [PROCESSING] {desc}")
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in process.stdout:
        if debug:
            sys.stdout.write(line)
        elif "frame=" in line:
            sys.stdout.write(f"\r   {line.strip()[:60]}")
            sys.stdout.flush()
    process.wait()


def process_video():
    usage_desc = (
        "M2 Max Video Assembler: Pro-grade quality with HOLD and --smooth support."
    )
    epilog_desc = """
QUALITY HACKS GUIDE:
-------------------
HOLD Syntax: filename.mp4 [timestamp] HOLD [duration]
Example: pella_1x.mp4 00:00:10.25 HOLD 4.0

--smooth: Enables 0.2s fade transitions. Replaces harsh jump cuts.
--lanczos: Best for Upscayl content. Preserves sharp edges when resizing.
--sharp [0.1 to 1.0]: Uses CAS sharpening. Best for AI video.
--grain [1 to 5]: Adds Film Grain to remove the 'plastic' AI look.
--pro: Maximum M2 Max hardware quality mode.
    """

    parser = argparse.ArgumentParser(
        description=usage_desc,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog_desc,
    )

    parser.add_argument("input", help="Text file (e.g., otsb.txt)")
    parser.add_argument("output", nargs="?", help="Output filename")
    parser.add_argument("--debug", action="store_true", help="Show FFmpeg logs")
    parser.add_argument(
        "--smooth", action="store_true", help="Enable smooth fade transitions"
    )
    parser.add_argument(
        "--lanczos", action="store_true", help="Enable high-end Lanczos scaling"
    )
    parser.add_argument(
        "--sharp", type=float, default=0.0, help="Sharpening level (0.1 - 1.0)"
    )
    parser.add_argument(
        "--grain", type=int, default=0, help="Film grain intensity (1 - 5)"
    )
    parser.add_argument(
        "--pro", action="store_true", help="Maximum M2 Max hardware quality"
    )
    parser.add_argument(
        "--asp43",
        action="store_true",
        help="Center-crop 16:9 video to 4:3 to remove side watermarks",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    base_name = os.path.splitext(args.input)[0]
    final_output = args.output if args.output else f"{base_name}_video.mp4"

    audio_bg_wav = f"{base_name}.wav"
    audio_bg_mp3 = f"{base_name}.mp3"

    if os.path.exists(audio_bg_wav):
        audio_bg = audio_bg_wav
        print(f"🎵 Audio: Using high-quality master ({audio_bg_wav})")
    elif os.path.exists(audio_bg_mp3):
        audio_bg = audio_bg_mp3
        print(f"🎵 Audio: Using standard file ({audio_bg_mp3})")
    else:
        audio_bg = None
        print("⚠️ Warning: No matching .wav or .mp3 found. Output will be silent.")

    temp_dir = tempfile.mkdtemp()

    to_process = []
    with open(args.input, "r") as f:
        for i, line in enumerate(f):
            tokens = line.split()
            if not tokens:
                continue
            fname = tokens[0]
            if not os.path.exists(fname):
                continue

            t1 = tokens[1] if len(tokens) > 1 else None
            t2 = tokens[2] if len(tokens) > 2 else None
            t3 = tokens[3] if len(tokens) > 3 else None

            ext = os.path.splitext(fname)[1].lower()
            is_img = ext in [".png", ".jpg", ".jpeg", ".webp"]
            is_hold = t2 and t2.upper() == "HOLD"

            if is_hold:
                hold_ts = t1 if t1 else "00:00:00"
                hold_dur = float(t3) if t3 else 3.0
                frame_path = os.path.join(temp_dir, f"hold_{i}.png")
                extract_cmd = f"{FFMPEG_PATH} -y -ss {hold_ts} -i {shlex.quote(fname)} -frames:v 1 {shlex.quote(frame_path)}"
                subprocess.run(extract_cmd, shell=True, capture_output=True)
                to_process.append(
                    {
                        "file": frame_path,
                        "start": 0.0,
                        "dur": hold_dur,
                        "is_img": True,
                        "label": f"HOLD {os.path.basename(fname)}",  # Removed colon
                    }
                )
            elif is_img:
                try:
                    duration = float(t1) if t1 else 6.0
                except:
                    duration = 6.0
                to_process.append(
                    {
                        "file": fname,
                        "start": 0.0,
                        "dur": duration,
                        "is_img": True,
                        "label": os.path.basename(fname),
                    }
                )
            else:
                start_val = parse_time(t1) if t1 else 0.0
                v_dur = get_video_duration(fname)
                duration = (parse_time(t2) - start_val) if t2 else (v_dur - start_val)
                to_process.append(
                    {
                        "file": fname,
                        "start": start_val,
                        "dur": duration,
                        "is_img": False,
                        "label": os.path.basename(fname),
                    }
                )

    processed_ts_files = []
    print(
        f"🚀 Render | 1080p | Smooth:{args.smooth} | Sharp:{args.sharp} | Grain:{args.grain}"
    )

    for i, cfg in enumerate(to_process):
        out_ts = os.path.join(temp_dir, f"part_{i:04d}.ts")

        # Escape colons for FFmpeg drawtext
        clean_label = cfg["label"].replace(":", "\\:")
        display_label = f"{clean_label} ({cfg['dur']:.2f}s)"

        scale_opt = "flags=lanczos+accurate_rnd" if args.lanczos else "flags=bicubic"
        filters = [
            f"scale={TARGET_RES}:force_original_aspect_ratio=decrease:{scale_opt}"
        ]
        filters.append(f"pad={TARGET_RES}:(ow-iw)/2:(oh-ih)/2")

        if args.sharp > 0:
            filters.append(f"cas={args.sharp}")
        if args.grain > 0:
            filters.append(f"noise=alls={args.grain}:allf=t+u")

        if args.smooth:
            fade_dur = 0.2
            if cfg["dur"] > (fade_dur * 2):
                filters.append(f"fade=t=in:st=0:d={fade_dur}")
                filters.append(f"fade=t=out:st={cfg['dur'] - fade_dur}:d={fade_dur}")

        if args.debug:
            text_f = f"drawtext=text='{display_label}':x=20:y=20:fontsize=32:fontcolor=yellow:box=1:boxcolor=black@0.5"
            filters.append(text_f)
        if args.asp43:
            # We place it first to ensure the base resolution is 4:3 before other effects
            filters.insert(0, "crop=ih*4/3:ih")

        filters.append("format=yuv420p")

        input_args = (
            f"-loop 1 -t {cfg['dur']}"
            if cfg["is_img"]
            else f"-ss {cfg['start']} -t {cfg['dur']}"
        )
        rt = "false" if args.pro else "true"

        cmd = (
            f'{FFMPEG_PATH} -y {input_args} -i {shlex.quote(cfg["file"])} -vf "{",".join(filters)}" '
            f"-r {FPS} -c:v h264_videotoolbox -b:v {BITRATE} "
            f"-realtime {rt} -profile:v high -f mpegts {out_ts}"
        )

        run_ffmpeg(cmd, cfg["label"], args.debug)
        processed_ts_files.append(out_ts)

    # Concat Section
    concat_file = os.path.join(temp_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for p in processed_ts_files:
            f.write(f"file '{p}'\n")

    print("\n🔗 Stitching...")
    subprocess.run(
        f"{FFMPEG_PATH} -y -f concat -safe 0 -i {shlex.quote(concat_file)} -c copy interim.mp4",
        shell=True,
    )

    if os.path.exists(audio_bg):
        subprocess.run(
            f"{FFMPEG_PATH} -y -i interim.mp4 -i {shlex.quote(audio_bg)} -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest {final_output}",
            shell=True,
        )
    else:
        if os.path.exists(final_output):
            os.remove(final_output)
        os.rename("interim.mp4", final_output)

    print(f"✅ Created: {final_output}")


if __name__ == "__main__":
    process_video()
