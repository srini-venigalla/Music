import subprocess
import os
import shlex
import re
import tempfile
import argparse

# --- PATHS & CONFIG ---
# Ensure these paths are correct for your system
FFMPEG_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
TARGET_RES = "1920:1080"
FPS = 24
BITRATE = "15M"
DEFAULT_DURATION = 6.0


def parse_time(t_str):
    if not t_str:
        return None
    try:
        if ":" not in t_str:
            return float(t_str)
        parts = t_str.split(":")
        # Handles H:M:S format
        return sum(float(x) * 60**i for i, x in enumerate(reversed(parts)))
    except ValueError:
        return None


def run_ffmpeg(cmd, desc, debug=False):
    """
    Restored: Now explicitly prints the description (filename/dur)
    and keeps it visible during the process.
    """
    print(f"\n🎬 [PROCESSING] {desc}")

    # Use stderr=subprocess.STDOUT because ffmpeg sends progress to stderr
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    for line in process.stdout:
        if debug:
            print(line, end="")
        else:
            # Show progress on the same line without wiping the 'desc' above
            if "frame=" in line or "time=" in line:
                stats = re.findall(
                    r"(frame=\s*\d+|fps=\s*[\d.]+|size=\s*\w+|time=\s*[\d:.]+)", line
                )
                print(f"\r   🚀 {' '.join(stats)}", end="", flush=True)

    process.wait()
    print(f"\n✅ Done with: {desc.split(':')[0]}")  # Short confirmation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Text file with script")
    parser.add_argument("-o", "--output", help="Final mp4 name")
    parser.add_argument("--pro", action="store_true", help="High quality encoding")
    parser.add_argument("--debug", action="store_true", help="Show full logs")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Error: {args.input} not found.")
        return

    base_name = os.path.splitext(args.input)[0]
    final_output = args.output if args.output else f"{base_name}_video.mp4"

    # Audio Logic
    audio_bg_wav = f"{base_name}.wav"
    audio_bg_mp3 = f"{base_name}.mp3"
    audio_bg = (
        audio_bg_wav
        if os.path.exists(audio_bg_wav)
        else (audio_bg_mp3 if os.path.exists(audio_bg_mp3) else None)
    )

    if audio_bg:
        print(f"🎵 Audio Found: {audio_bg}")
    else:
        print("⚠️ No audio found (.wav/.mp3). Output will be silent.")

    temp_dir = tempfile.mkdtemp()
    script_items = []

    with open(args.input, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = re.split(r"\s+", line)
            fname = parts[0]

            # Duration logic
            dur = parse_time(parts[1]) if len(parts) >= 2 else DEFAULT_DURATION
            # Start time logic
            start = parse_time(parts[2]) if len(parts) > 2 else 0.0

            if not os.path.exists(fname):
                print(f"❓ Skip: {fname} (File not found)")
                continue

            is_img = fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            script_items.append(
                {"file": fname, "dur": dur, "start": start, "is_img": is_img}
            )

    if not script_items:
        print("❌ No valid files to process.")
        return

    processed_ts_files = []
    for i, cfg in enumerate(script_items):
        # This label is now preserved in the console
        label = f"{cfg['file']} | Duration: {cfg['dur']}s | Start: {cfg['start']}s"
        out_ts = os.path.join(temp_dir, f"part_{i:03d}.ts")

        filters = [
            f"scale={TARGET_RES}:force_original_aspect_ratio=decrease",
            f"pad={TARGET_RES}:(ow-iw)/2:(oh-ih)/2",
            "setsar=1",
            "format=yuv420p",
        ]

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

        run_ffmpeg(cmd, label, args.debug)
        processed_ts_files.append(out_ts)

    # Concatenation
    concat_file = os.path.join(temp_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for p in processed_ts_files:
            f.write(f"file '{p}'\n")

    print("\n🔗 Stitching parts together...")
    subprocess.run(
        f"{FFMPEG_PATH} -y -f concat -safe 0 -i {shlex.quote(concat_file)} -c copy interim.mp4",
        shell=True,
    )

    if audio_bg:
        print(f"🎸 Mastering with audio: {audio_bg}")
        subprocess.run(
            f"{FFMPEG_PATH} -y -i interim.mp4 -i {shlex.quote(audio_bg)} -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest {shlex.quote(final_output)}",
            shell=True,
        )
    else:
        if os.path.exists(final_output):
            os.remove(final_output)
        os.rename("interim.mp4", final_output)

    print(f"\n✨ Success! Final Video: {final_output}")


if __name__ == "__main__":
    main()
