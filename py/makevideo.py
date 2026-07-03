import subprocess
import os
import sys
import shlex
import re
import tempfile
import argparse

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


def sbv_to_srt(sbv_path):
    """Converts YouTube .sbv format to .srt for FFmpeg filter compatibility."""
    srt_path = sbv_path.replace(".sbv", ".srt")
    try:
        with open(sbv_path, "r", encoding="utf-8") as f:
            content = f.read()

        # SBV: 0:00:02.042,0:00:05.409 -> SRT: 00:00:02,042 --> 00:00:05,409
        def fix_time(match):
            t1, t2 = match.groups()

            def fmt(t):
                p = t.split(":")
                if len(p[0]) == 1:
                    p[0] = "0" + p[0]
                return ":".join(p).replace(".", ",")

            return f"{fmt(t1)} --> {fmt(t2)}"

        converted = re.sub(r"(\d+:\d+:\d+\.\d+),(\d+:\d+:\d+\.\d+)", fix_time, content)
        blocks = [b.strip() for b in converted.split("\n\n") if b.strip()]

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, block in enumerate(blocks, 1):
                f.write(f"{i}\n{block}\n\n")
        return srt_path
    except Exception as e:
        print(f"⚠️ Subtitle conversion failed: {e}")
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
    return process.returncode


def process_video():
    parser = argparse.ArgumentParser(description="M2 Max Video Assembler")
    parser.add_argument("input", help="Text file (e.g., otsb.txt)")
    parser.add_argument("output", nargs="?", help="Output filename")
    parser.add_argument("--subs", help="Path to captions.sbv")
    parser.add_argument("--debug", action="store_true", help="Show FFmpeg logs")
    parser.add_argument("--smooth", action="store_true", help="Enable 0.2s transitions")
    parser.add_argument("--lanczos", action="store_true", help="Enable Lanczos scaling")
    parser.add_argument("--sharp", type=float, default=0.0, help="Sharpening (0.1-1.0)")
    parser.add_argument("--grain", type=int, default=0, help="Grain (1-5)")
    parser.add_argument("--pro", action="store_true", help="Max quality mode")
    parser.add_argument("--asp43", action="store_true", help="Crop 16:9 to 4:3")
    parser.add_argument("--cover", action="store_true", help="Fill 16:9 frame fully (scale-to-cover, crop overflow)")
    parser.add_argument("--captions", action="store_true", help="Render per-clip captions from input file")
    parser.add_argument("--caption-font", default="Anek Telugu", help="Font for per-clip captions (fontconfig name)")
    parser.add_argument("--caption-size", type=int, default=36, help="Font size for per-clip captions")
    parser.add_argument("--caption-margin", type=int, default=12, help="Pixels from bottom edge to caption baseline")
    parser.add_argument("--caption-color", default="0xFFFF54", help="Caption fill color (ffmpeg syntax: name, #rgb, 0xRRGGBB)")
    parser.add_argument("--caption-stroke", default="black", help="Caption outline color")
    parser.add_argument("--caption-stroke-width", type=int, default=1, help="Caption outline thickness in pixels (0 disables)")
    parser.add_argument("--caption-weight", default=None, help="Font weight: name (bold, semibold, light), CSS 100-900, or fontconfig 0-210")

    args = parser.parse_args()
    base_name = os.path.splitext(args.input)[0]
    final_output = args.output if args.output else f"{base_name}_video.mp4"

    # Convert subtitles if provided
    srt_path = sbv_to_srt(args.subs) if args.subs else None

    audio_bg = next(
        (f for f in [f"{base_name}.wav", f"{base_name}.mp3"] if os.path.exists(f)), None
    )
    temp_dir = tempfile.mkdtemp()
    to_process = []

    with open(args.input, "r") as f:
        for i, line in enumerate(f):
            # Extract optional double-quoted caption, then tokenize the rest
            line = line.rstrip("\n")
            cap_match = re.search(r'"([^"]*)"', line)
            if cap_match:
                caption = cap_match.group(1)
                main_part = line[: cap_match.start()] + line[cap_match.end() :]
            else:
                caption = None
                main_part = line
            tokens = main_part.split()
            if not tokens or not os.path.exists(tokens[0]):
                continue
            fname = tokens[0]
            t1 = tokens[1] if len(tokens) > 1 else None
            t2 = tokens[2] if len(tokens) > 2 else None
            t3 = tokens[3] if len(tokens) > 3 else None

            is_img = os.path.splitext(fname)[1].lower() in [
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
            ]
            if t2 and t2.upper() == "HOLD":
                frame_path = os.path.join(temp_dir, f"hold_{i}.png")
                subprocess.run(
                    f"{FFMPEG_PATH} -y -ss {t1 or '0'} -i {shlex.quote(fname)} -frames:v 1 {shlex.quote(frame_path)}",
                    shell=True,
                    capture_output=True,
                )
                to_process.append(
                    {
                        "file": frame_path,
                        "start": 0.0,
                        "dur": float(t3 or 3.0),
                        "is_img": True,
                        "label": f"HOLD {os.path.basename(fname)}",
                        "caption": caption,
                    }
                )
            elif is_img:
                to_process.append(
                    {
                        "file": fname,
                        "start": 0.0,
                        "dur": float(t1 or 6.0),
                        "is_img": True,
                        "label": os.path.basename(fname),
                        "caption": caption,
                    }
                )
            else:
                s = parse_time(t1) or 0.0
                d = (parse_time(t2) - s) if t2 else (get_video_duration(fname) - s)
                to_process.append(
                    {
                        "file": fname,
                        "start": s,
                        "dur": d,
                        "is_img": False,
                        "label": os.path.basename(fname),
                        "caption": caption,
                    }
                )

    processed_ts_files = []
    target_w, target_h = [int(x) for x in TARGET_RES.split(":")]
    print(f"🚀 Render | Asp43:{args.asp43} | Subs:{'Yes' if srt_path else 'No'}")

    frame_offset = 0
    time_offset = 0.0
    for i, cfg in enumerate(to_process):
        out_ts = os.path.join(temp_dir, f"part_{i:04d}.ts")
        clean_label = cfg["label"].replace(":", "\\:")
        display_label = f"{clean_label} ({cfg['dur']:.2f}s)"
        scale_opt = "flags=lanczos+accurate_rnd" if args.lanczos else "flags=bicubic"
        filters = [f"fps={FPS}"]

        if args.asp43:
            filters.append(f"scale=-2:{target_h}:{scale_opt}")
            filters.append(f"crop='min(iw, {target_h}*4/3)':'min(ih, {target_h})'")
            filters.append(f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black")
        elif args.cover:
            filters.append(
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase:{scale_opt}"
            )
            filters.append(f"crop={target_w}:{target_h}")
        else:
            filters.append(
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease:{scale_opt}"
            )
            filters.append(f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2")

        filters.append("setsar=sar=1/1")
        if args.sharp > 0:
            filters.append(f"cas={args.sharp}")
        if args.grain > 0:
            filters.append(f"noise=alls={args.grain}:allf=t+u")
        if args.smooth and cfg["dur"] > 0.4:
            filters.append(
                "fade=t=in:st=0:d=0.2,fade=t=out:st=" + f"{cfg['dur'] - 0.2}:d=0.2"
            )
        caption_filter = None
        if args.captions and cfg.get("caption"):
            cap_file = os.path.join(temp_dir, f"cap_{i:04d}.txt")
            with open(cap_file, "w", encoding="utf-8") as cf:
                cf.write(cfg["caption"])
            esc_cap_path = cap_file.replace("\\", "\\\\").replace(":", "\\:")
            # When weight is specified, resolve via fc-match to a concrete .ttf
            # path; ffmpeg's font= parameter doesn't accept fontconfig patterns.
            font_clause = f"font='{args.caption_font}'"
            if args.caption_weight:
                css_to_fc = {100: 0, 200: 40, 300: 50, 400: 80, 500: 100,
                             600: 180, 700: 200, 800: 205, 900: 210}
                w = args.caption_weight
                try:
                    n = int(w)
                    w = str(css_to_fc[n]) if n in css_to_fc else str(n)
                except ValueError:
                    pass
                try:
                    fc_out = subprocess.check_output(
                        ["fc-match", "-f", "%{file}",
                         f"{args.caption_font}:weight={w}"],
                        text=True, stderr=subprocess.STDOUT,
                    ).strip()
                    if fc_out and os.path.exists(fc_out):
                        esc_font_path = fc_out.replace("\\", "\\\\").replace(":", "\\:")
                        font_clause = f"fontfile={esc_font_path}"
                    else:
                        print(f"   ⚠ fc-match returned unusable path {fc_out!r}; falling back to family lookup")
                except FileNotFoundError:
                    print("   ⚠ fc-match not on PATH; falling back to family lookup")
                except subprocess.CalledProcessError as e:
                    print(f"   ⚠ fc-match exited {e.returncode}; falling back to family lookup")
                except Exception as e:
                    print(f"   ⚠ fc-match failed ({e!r}); falling back to family lookup")
            caption_filter = (
                f"drawtext={font_clause}:textfile={esc_cap_path}:"
                f"x=(w-text_w)/2:y=h-text_h-{args.caption_margin}:"
                f"fontsize={args.caption_size}:fontcolor={args.caption_color}:"
                f"bordercolor={args.caption_stroke}:borderw={args.caption_stroke_width}"
            )
            filters.append(caption_filter)
        if args.debug:
            filters.append(
                f"drawtext=text='{display_label}  f#%{{eif\\:n+{frame_offset}\\:d}}  "
                f"t=%{{pts\\:hms}}  T=%{{pts\\:hms\\:{time_offset}}}':"
                "x=20:y=20:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6"
            )

        filters.append("format=yuv420p")
        in_args = (
            f"-loop 1 -t {cfg['dur']}"
            if cfg["is_img"]
            else f"-ss {cfg['start']} -t {cfg['dur']}"
        )

        def build_cmd(filt):
            return (
                f'{FFMPEG_PATH} -y {in_args} -i {shlex.quote(cfg["file"])} -vf "{",".join(filt)}" '
                f"-r {FPS} -c:v h264_videotoolbox -b:v {BITRATE} -realtime {'false' if args.pro else 'true'} "
                f"-profile:v high -f mpegts {out_ts}"
            )

        rc = run_ffmpeg(build_cmd(filters), cfg["label"], args.debug)
        ok = rc == 0 and os.path.exists(out_ts) and os.path.getsize(out_ts) > 0
        if not ok and caption_filter is not None:
            print(f"\n   ⚠ caption render failed for {cfg['label']}; retrying without caption")
            filters.remove(caption_filter)
            rc = run_ffmpeg(build_cmd(filters), cfg["label"] + " (no caption)", args.debug)
            ok = rc == 0 and os.path.exists(out_ts) and os.path.getsize(out_ts) > 0
        if ok:
            processed_ts_files.append(out_ts)
        frame_offset += round(cfg["dur"] * FPS)
        time_offset += cfg["dur"]

    concat_file = os.path.join(temp_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for p in processed_ts_files:
            f.write(f"file '{p}'\n")

    print("\n🔗 Stitching and Hard-burning Subtitles...")
    # Stitch parts into a high-quality interim file
    interim_mp4 = os.path.join(temp_dir, "interim.mp4")
    subprocess.run(
        f"{FFMPEG_PATH} -y -f concat -safe 0 -i {shlex.quote(concat_file)} -c copy {interim_mp4}",
        shell=True,
    )

    # Prepare Final Pass (Merge Audio + Burn Subtitles)
    final_filters = []
    if srt_path:
        font_file = "Anek Telugu"
        # Escape path for FFmpeg filter (MacOS colons)
        esc_path = srt_path.replace(":", "\\:").replace("'", "'\\\\''")
        # Style: White text, thin outline, yellow shadow for visibility
        style = f"FontSize=20,FontName={font_file},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Shadow=1"
        final_filters.append(f"subtitles='{esc_path}':force_style='{style}'")

    filter_cmd = f'-vf "{",".join(final_filters)}"' if final_filters else ""
    audio_cmd = (
        f"-i {shlex.quote(audio_bg)} -map 0:v:0 -map 1:a:0 -shortest"
        if audio_bg
        else ""
    )

    # We must re-encode to burn subtitles
    cmd = (
        f"{FFMPEG_PATH} -y -i {interim_mp4} {audio_cmd} {filter_cmd} "
        f"-c:v h264_videotoolbox -b:v {BITRATE} -c:a aac -b:a 192k {final_output}"
    )

    subprocess.run(cmd, shell=True)
    print(f"\n✅ Created: {final_output}")
    print("Options used:")
    for k, v in vars(args).items():
        print(f"  --{k.replace('_', '-')}: {v}")


if __name__ == "__main__":
    process_video()
