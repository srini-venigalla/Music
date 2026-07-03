import subprocess
import os
import sys
import shlex
import re
import tempfile
import argparse

# --- CHANGE HISTORY ---
# 2026-03-29: Finalized --asp43 with bitand math and SAR reset to fix .ts concat failures.
# 2026-03-22: Added HOLD functionality to freeze video frames at specific timestamps.
# 2026-01-15: Optimized for M2 Max using h264_videotoolbox.

# --- PATHS & CONFIG ---
FFMPEG_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
TARGET_RES = "1920:1080"
FPS = 24
BITRATE = "15M"

def get_video_duration(filename):
    cmd = [
        FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", filename
    ]
    try:
        out = subprocess.check_output(cmd).decode().strip()
        return float(out)
    except:
        return 0.0

def parse_time(t_str):
    if not t_str: return None
    try:
        if ":" not in t_str: return float(t_str)
        parts = t_str.split(":")
        return sum(float(x) * 60**i for i, x in enumerate(reversed(parts)))
    except ValueError: return None

def run_ffmpeg(cmd, desc, debug=False):
    print(f"\n▶️  [PROCESSING] {desc}")
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in process.stdout:
        if debug: sys.stdout.write(line)
        elif "frame=" in line:
            sys.stdout.write(f"\r   {line.strip()[:60]}")
            sys.stdout.flush()
    process.wait()

def process_video():
    parser = argparse.ArgumentParser(description="M2 Max Video Assembler")
    parser.add_argument("input", help="Text file (e.g., otsb.txt)")
    parser.add_argument("output", nargs="?", help="Output filename")
    parser.add_argument("--debug", action="store_true", help="Show FFmpeg logs")
    parser.add_argument("--smooth", action="store_true", help="Enable 0.2s transitions")
    parser.add_argument("--lanczos", action="store_true", help="Enable Lanczos scaling")
    parser.add_argument("--sharp", type=float, default=0.0, help="Sharpening (0.1-1.0)")
    parser.add_argument("--grain", type=int, default=0, help="Grain (1-5)")
    parser.add_argument("--pro", action="store_true", help="Max quality mode")
    parser.add_argument("--asp43", action="store_true", help="Crop 16:9 to 4:3")

    args = parser.parse_args()
    base_name = os.path.splitext(args.input)[0]
    final_output = args.output if args.output else f"{base_name}_video.mp4"

    audio_bg = next((f for f in [f"{base_name}.wav", f"{base_name}.mp3"] if os.path.exists(f)), None)
    temp_dir = tempfile.mkdtemp()
    to_process = []

    with open(args.input, "r") as f:
        for i, line in enumerate(f):
            tokens = line.split()
            if not tokens or not os.path.exists(tokens[0]): continue
            fname = tokens[0]
            t1, t2, t3 = (tokens[1] if len(tokens) > 1 else None), (tokens[2] if len(tokens) > 2 else None), (tokens[3] if len(tokens) > 3 else None)
            
            is_img = os.path.splitext(fname)[1].lower() in [".png", ".jpg", ".jpeg", ".webp"]
            if t2 and t2.upper() == "HOLD":
                frame_path = os.path.join(temp_dir, f"hold_{i}.png")
                subprocess.run(f"{FFMPEG_PATH} -y -ss {t1 or '0'} -i {shlex.quote(fname)} -frames:v 1 {shlex.quote(frame_path)}", shell=True, capture_output=True)
                to_process.append({"file": frame_path, "start": 0.0, "dur": float(t3 or 3.0), "is_img": True, "label": f"HOLD {os.path.basename(fname)}"})
            elif is_img:
                to_process.append({"file": fname, "start": 0.0, "dur": float(t1 or 6.0), "is_img": True, "label": os.path.basename(fname)})
            else:
                s = parse_time(t1) or 0.0
                d = (parse_time(t2) - s) if t2 else (get_video_duration(fname) - s)
                to_process.append({"file": fname, "start": s, "dur": d, "is_img": False, "label": os.path.basename(fname)})

    processed_ts_files = []
    target_w, target_h = [int(x) for x in TARGET_RES.split(":")]
    print(f"🚀 Render | Asp43:{args.asp43} | Sharp:{args.sharp} | Grain:{args.grain}")

    for i, cfg in enumerate(to_process):
        out_ts = os.path.join(temp_dir, f"part_{i:04d}.ts")
        
        # Escape colons for FFmpeg drawtext
        clean_label = cfg["label"].replace(":", "\\:")
        display_label = f"{clean_label} ({cfg['dur']:.2f}s)"
        
        scale_opt = "flags=lanczos+accurate_rnd" if args.lanczos else "flags=bicubic"
        filters = []
        
        if args.asp43:
            # 1. Scale height to 1080 immediately to make math predictable
            # 2. Crop to a 4:3 area (1440 width)
            # 3. 'min' logic prevents 'too big' errors on vertical 9:16 clips
            filters.append(f"scale=-2:{target_h}:{scale_opt}")
            filters.append(f"crop='min(iw, {target_h}*4/3)':'min(ih, {target_h})'")
            # 4. Pad back to 1920x1080 to restore the 'pillars' and fix the aspect ratio
            filters.append(f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black")
        else:
            # Your original working else part
            filters.append(f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease:{scale_opt}")
            filters.append(f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2")
        
        filters.append("setsar=sar=1/1")

        if args.sharp > 0: filters.append(f"cas={args.sharp}")
        if args.grain > 0: filters.append(f"noise=alls={args.grain}:allf=t+u")
        if args.smooth and cfg["dur"] > 0.4:
            filters.append("fade=t=in:st=0:d=0.2,fade=t=out:st=" + f"{cfg['dur']-0.2}:d=0.2")
        if args.debug:
            #label = cfg["label"].replace(":", "\\:")
            filters.append(f"drawtext=text='{display_label}':x=20:y=20:fontsize=32:fontcolor=yellow:box=1:boxcolor=black@0.5")
        
        filters.append("format=yuv420p")
        in_args = f"-loop 1 -t {cfg['dur']}" if cfg["is_img"] else f"-ss {cfg['start']} -t {cfg['dur']}"
        
        cmd = (f'{FFMPEG_PATH} -y {in_args} -i {shlex.quote(cfg["file"])} -vf "{",".join(filters)}" '
               f"-r {FPS} -c:v h264_videotoolbox -b:v {BITRATE} -realtime {'false' if args.pro else 'true'} "
               f"-profile:v high -f mpegts {out_ts}")

        run_ffmpeg(cmd, cfg["label"], args.debug)
        
        if os.path.exists(out_ts) and os.path.getsize(out_ts) > 0:
            processed_ts_files.append(out_ts)
        else:
            print(f"\n❌ FATAL: Part {i} failed to render. Stopping.")
            sys.exit(1)

    concat_file = os.path.join(temp_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for p in processed_ts_files: f.write(f"file '{p}'\n")

    print("\n🔗 Stitching...")
    subprocess.run(f"{FFMPEG_PATH} -y -f concat -safe 0 -i {shlex.quote(concat_file)} -c copy interim.mp4", shell=True)

    if audio_bg:
        subprocess.run(f"{FFMPEG_PATH} -y -i interim.mp4 -i {shlex.quote(audio_bg)} -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest {final_output}", shell=True)
    else:
        if os.path.exists(final_output): os.remove(final_output)
        os.rename("interim.mp4", final_output)

    print(f"✅ Created: {final_output}")

if __name__ == "__main__":
    process_video()