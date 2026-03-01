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
    """
    Robust parser for filenames with spaces/parentheses and optional timestamps.
    """
    line = line.strip()
    if not line:
        return None, None, None
    # Remove source tags
    line = re.sub(r"^\\s*", "", line)
    # Match timestamps at the end
    ts_match = re.search(r"\s+(\d+[:\d.]*)\s*(\d+[:\d.]*)?$", line)
    if ts_match:
        filename = line[: ts_match.start()].strip()
        return filename, ts_match.group(1), ts_match.group(2)
    return line, None, None


def generate_workflow(input_file, speed, debug, smooth):
    if not os.path.exists(input_file):
        print(f"❌ Input file '{input_file}' not found.")
        return

    base_name = os.path.splitext(input_file)[0]
    interim_dir = tempfile.mkdtemp(prefix="video_render_")
    concat_file = os.path.join(interim_dir, "list.txt")
    interim_video = os.path.join(interim_dir, "stitched_raw.mp4")
    audio_bg = f"{base_name}.mp3"
    final_output = f"{base_name}_video.mp4"

    pts_factor = 1.0 / speed
    video_configs = []

    # --- PRE-FLIGHT CHECK ---
    with open(input_file, "r") as f:
        for i, line in enumerate(f, 1):
            if not line.strip() or line.startswith("#"):
                continue
            fname, start, end = parse_line(line)
            if os.path.exists(fname):
                video_configs.append({"file": fname, "start": start, "end": end})
            else:
                print(f"⚠️ Line {i}: File not found -> '{fname}'")

    if not video_configs:
        print("🛑 No valid files found. Check your paths.")
        return

    print(f"🚀 Processing {len(video_configs)} items (Speed: {speed}x)...")

    # --- PHASE 1: INDIVIDUAL NORMALIZATION ---
    processed_ts_files = []
    for i, cfg in enumerate(video_configs):
        out_ts = os.path.join(interim_dir, f"part_{i:03d}.ts")
        ext = os.path.splitext(cfg["file"])[1].lower()
        is_img = ext in [".jpg", ".jpeg", ".png", ".webp"]

        raw_dur = get_duration(cfg["file"], cfg["start"], cfg["end"])
        final_dur = raw_dur * pts_factor if is_img else raw_dur

        debug_filter = (
            f",drawtext=text='{os.path.basename(cfg['file'])}':x=20:y=20:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.5"
            if debug
            else ""
        )
        smooth_filter = (
            f",minterpolate=fps={FPS}:mi_mode=mci"
            if (smooth and not is_img)
            else ""
        )
        v_speed = f"setpts={pts_factor}*PTS"

        a_val = speed
        if a_val < 0.5:
            a_speed = f"atempo=0.5,atempo={a_val / 0.5}"
        elif a_val > 2.0:
            a_speed = f"atempo=2.0,atempo={a_val / 2.0}"
        else:
            a_speed = f"atempo={a_val}"

        vf = f"scale={TARGET_RES}:force_original_aspect_ratio=decrease,pad={TARGET_RES}:(ow-iw)/2:(oh-ih)/2,{v_speed}{smooth_filter},fps={FPS},format=yuv420p{debug_filter}"

        print(f"  [{i + 1}/{len(video_configs)}] {os.path.basename(cfg['file'])}")

        if is_img:
            cmd = (
                f"ffmpeg -y -loop 1 -t {final_dur} -i {shlex.quote(cfg['file'])} "
                f"-f lavfi -i anullsrc=r=48000:cl=stereo -t {final_dur} "
                f'-vf "{vf}" -c:v libx264 -preset superfast -c:a aac {out_ts}'
            )
        else:
            ss = f"-ss {cfg['start']}" if cfg["start"] else ""
            to = f"-to {cfg['end']}" if cfg["end"] else ""
            cmd = (
                f"ffmpeg -y {ss} {to} -i {shlex.quote(cfg['file'])} "
                f'-vf "{vf}" -af "{a_speed}" -c:v libx264 -preset superfast -c:a aac -ar 48000 -ac 2 {out_ts}'
            )

        subprocess.run(
            cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        processed_ts_files.append(out_ts)

    # --- PHASE 2: STITCHING (Re-encoding for a unified stream) ---
    with open(concat_file, "w") as f:
        for p in processed_ts_files:
            f.write(f"file '{p}'\n")

    print(f"\n🔗 Phase 2: Stitching and repairing stream...")
    subprocess.run(
        f"ffmpeg -y -f concat -safe 0 -i {concat_file} -c:v libx264 -preset superfast -pix_fmt yuv420p -c:a aac {interim_video}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # --- PHASE 3: FINAL AUDIO MIX ---
    if os.path.exists(audio_bg):
        print(f"🎵 Phase 3: Mixing background audio: {audio_bg}")
        subprocess.run(
            f"ffmpeg -y -i {interim_video} -i {shlex.quote(audio_bg)} -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest {final_output}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        if os.path.exists(final_output):
            os.remove(final_output)
        os.rename(interim_video, final_output)

    print(f"\n✅ Final Video: {final_output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--speed", type=float, default=1.0, help="0.5=Slow, 2.0=Fast")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--smooth", action="store_true")
    args = parser.parse_args()
    generate_workflow(args.input, args.speed, args.debug, args.smooth)
