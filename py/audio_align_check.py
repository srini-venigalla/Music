#!/usr/bin/env python3
"""Render audio waveform with clip-boundary markers from a shot list.

Computes cumulative clip end times using the same parser as makevideo.py,
then overlays vertical lines on a single wide waveform PNG so misaligned
boundaries jump out visually.

With --onsets (default on), runs librosa onset detection and draws a green
line at the nearest detected audio onset for each video boundary, plus a
delta label in milliseconds.

Usage:
    audio_align_check.py <shotlist.txt> <audio.{wav,mp3}> <out.png>
"""
import argparse
import bisect
import os
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FFMPEG_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


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


def get_duration(path):
    cmd = [FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", path]
    try:
        return float(subprocess.check_output(cmd).decode().strip())
    except Exception:
        return 0.0


def parse_shotlist(path):
    """Return list of (label, duration_seconds) for each non-skipped line."""
    shot_dir = Path(path).parent
    clips = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            cap_match = re.search(r'"([^"]*)"', line)
            if cap_match:
                line = line[:cap_match.start()] + line[cap_match.end():]
            tokens = line.split()
            if not tokens:
                continue
            fname = tokens[0]
            full = fname if os.path.isabs(fname) else str(shot_dir / fname)
            if not os.path.exists(full):
                continue
            t1 = tokens[1] if len(tokens) > 1 else None
            t2 = tokens[2] if len(tokens) > 2 else None
            t3 = tokens[3] if len(tokens) > 3 else None
            ext = os.path.splitext(fname)[1].lower()
            is_img = ext in (".png", ".jpg", ".jpeg", ".webp")
            if t2 and t2.upper() == "HOLD":
                dur = float(t3 or 3.0)
            elif is_img:
                dur = float(t1 or 6.0)
            else:
                s = parse_time(t1) or 0.0
                dur = (parse_time(t2) - s) if t2 else (get_duration(full) - s)
            clips.append((os.path.basename(fname), float(dur)))
    return clips


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def detect_onsets(audio_path, sr=22050):
    import librosa
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    onset_times = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=True)
    return list(map(float, onset_times))


def nearest_onset(onsets, t):
    if not onsets:
        return None
    i = bisect.bisect_left(onsets, t)
    candidates = []
    if i > 0:
        candidates.append(onsets[i - 1])
    if i < len(onsets):
        candidates.append(onsets[i])
    return min(candidates, key=lambda o: abs(o - t))


def annotate(wave_path, out_path, boundaries, onsets, pps, label_strip):
    wave = Image.open(wave_path).convert("RGBA")
    canvas = Image.new("RGBA", (wave.width, wave.height + label_strip), (20, 20, 20, 255))
    canvas.paste(wave, (0, label_strip))
    draw = ImageDraw.Draw(canvas)

    idx_font = load_font(13)
    name_font = load_font(11)
    delta_font = load_font(10)

    line_color = (255, 60, 60, 220)
    onset_color = (90, 255, 110, 200)
    box_fill = (0, 0, 0, 210)
    idx_color = (255, 255, 84, 255)
    name_color = (220, 220, 220, 255)
    delta_pos = (110, 255, 110, 255)
    delta_neg = (255, 140, 140, 255)
    pad = 2

    # Draw onset lines first so boundary lines render on top of them
    for o in onsets:
        x = int(o * pps)
        if 0 <= x < canvas.width:
            draw.line([(x, label_strip), (x, canvas.height - 1)],
                      fill=onset_color, width=1)

    for idx, label, t, near, delta in boundaries:
        x = int(t * pps)
        if not (0 <= x < canvas.width):
            continue

        idx_text = str(idx)
        bbox = draw.textbbox((x + 3, 3), idx_text, font=idx_font)
        box_rect = [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad]
        draw.rectangle(box_rect, fill=box_fill)
        draw.text((x + 3, 3), idx_text, fill=idx_color, font=idx_font)
        box_bottom = box_rect[3]

        if delta is not None:
            sign = "+" if delta >= 0 else ""
            d_text = f"{sign}{int(round(delta * 1000))}ms"
            d_color = delta_pos if delta >= 0 else delta_neg
            d_bbox = draw.textbbox((x + 3, box_bottom + 1), d_text, font=delta_font)
            d_rect = [d_bbox[0] - 1, d_bbox[1] - 1, d_bbox[2] + 1, d_bbox[3] + 1]
            draw.rectangle(d_rect, fill=box_fill)
            draw.text((x + 3, box_bottom + 1), d_text, fill=d_color, font=delta_font)
            box_bottom = d_rect[3]

        tb = name_font.getbbox(label)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        text_img = Image.new("RGBA", (tw + 4, th + 4), (0, 0, 0, 0))
        ImageDraw.Draw(text_img).text((2, 1), label, fill=name_color, font=name_font)
        rotated = text_img.rotate(-90, expand=True)
        paste_x = x - rotated.width // 2 + 1
        paste_y = box_bottom + 3
        if paste_y + rotated.height > label_strip:
            crop_h = label_strip - paste_y
            if crop_h > 0:
                rotated = rotated.crop((0, 0, rotated.width, crop_h))
            else:
                rotated = None
        if rotated is not None:
            canvas.paste(rotated, (paste_x, paste_y), rotated)

        # Red boundary line (drawn over onsets so the cut is dominant)
        draw.line([(x, box_bottom + 1), (x, canvas.height - 1)], fill=line_color, width=1)

    canvas.convert("RGB").save(out_path)


def main():
    ap = argparse.ArgumentParser(description="Audio waveform with clip-boundary markers")
    ap.add_argument("shotlist")
    ap.add_argument("audio")
    ap.add_argument("output")
    ap.add_argument("--pps", type=int, default=60, help="Pixels per second of audio (default 60)")
    ap.add_argument("--height", type=int, default=240, help="Waveform height in pixels (default 240)")
    ap.add_argument("--color", default="cyan", help="Waveform color (default cyan)")
    ap.add_argument("--label-strip", type=int, default=170,
                    help="Pixels above waveform reserved for labels (default 170)")
    ap.add_argument("--no-onsets", action="store_true",
                    help="Skip librosa onset detection (red lines only)")
    ap.add_argument("--threshold-ms", type=int, default=50,
                    help="Flag boundaries off by more than this many ms (default 50)")
    args = ap.parse_args()

    audio_dur = get_duration(args.audio)
    if audio_dur <= 0:
        raise SystemExit(f"Could not probe audio duration of {args.audio}")
    clips = parse_shotlist(args.shotlist)
    total_clip_dur = sum(d for _, d in clips)
    width = max(int(audio_dur * args.pps), 100)

    onsets = []
    if not args.no_onsets:
        print("Running librosa onset detection...")
        onsets = detect_onsets(args.audio)
        print(f"  detected {len(onsets)} onsets")

    print(f"Audio: {args.audio}  ({audio_dur:.2f}s)")
    print(f"Image: {width} x {args.height + args.label_strip} px @ {args.pps} px/s")
    print(f"Clips: {len(clips)}  total visual {total_clip_dur:.2f}s "
          f"(delta vs audio: {total_clip_dur - audio_dur:+.3f}s)")

    cum = 0.0
    boundaries = []  # (idx, label, t, nearest_onset, delta)
    for i, (label, dur) in enumerate(clips, 1):
        cum += dur
        near = nearest_onset(onsets, cum) if onsets else None
        delta = (near - cum) if near is not None else None
        boundaries.append((i, label, cum, near, delta))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tmp_wave = tf.name
    try:
        cmd = [FFMPEG_PATH, "-y", "-i", args.audio,
               "-filter_complex",
               f"showwavespic=s={width}x{args.height}:colors={args.color}",
               "-frames:v", "1", "-update", "1", tmp_wave]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        annotate(tmp_wave, args.output, boundaries, onsets, args.pps, args.label_strip)
    finally:
        if os.path.exists(tmp_wave):
            os.remove(tmp_wave)

    print(f"\n✅ Wrote {args.output}")

    print("\n# Clip-end timeline:")
    for idx, label, t, near, delta in boundaries:
        m, s = divmod(t, 60)
        suffix = ""
        if delta is not None:
            sign = "+" if delta >= 0 else ""
            suffix = f"  Δ {sign}{int(round(delta * 1000)):>5}ms"
        if t > audio_dur + 0.05:
            suffix += "  ⚠ past audio end"
        print(f"  {idx:3d}  {int(m):02d}:{s:06.3f}  {label:30s}{suffix}")

    if onsets:
        flagged = [(i, lbl, t, d) for (i, lbl, t, n, d) in boundaries
                   if d is not None and abs(d) * 1000 > args.threshold_ms]
        flagged.sort(key=lambda x: -abs(x[3]))
        print(f"\n# Boundaries off > {args.threshold_ms}ms ({len(flagged)} of {len(boundaries)}):")
        for i, lbl, t, d in flagged:
            sign = "+" if d >= 0 else ""
            print(f"  {i:3d}  {sign}{int(round(d*1000)):>5}ms   t={t:7.3f}s   {lbl}")


if __name__ == "__main__":
    main()
