import argparse
import json
import os
import re
import subprocess
import sys


def timestamp_to_ms(ts):
    """Converts HH:MM:SS.mmm to total milliseconds."""
    try:
        h, m, s = ts.strip().split(":")
        seconds, ms = s.split(".")
        total_ms = (
            (int(h) * 3600000) + (int(m) * 60000) + (int(seconds) * 1000) + int(ms)
        )
        return total_ms
    except ValueError:
        print(f"Error parsing timestamp: {ts}")
        return None


def cue_to_ms(cue, fps):
    """Convert a cue string to ms. `HH:MM:SS.mmm` → timestamp, bare integer → frame."""
    cue = cue.strip()
    if ":" in cue:
        return timestamp_to_ms(cue)
    try:
        frame = int(cue)
    except ValueError:
        print(f"Error parsing cue (not a timestamp or frame number): {cue}")
        return None
    return round(frame * 1000 / fps)


def get_audio_duration_ms(path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    try:
        out = subprocess.check_output(cmd).decode().strip()
        return int(round(float(out) * 1000))
    except Exception:
        return None


def build_mix_filter(cues, fps, anchor_pct, sfx_ms):
    anchor_offset = round((anchor_pct / 100.0) * sfx_ms) if sfx_ms else 0
    filter_parts = []
    inputs_count = 0
    for i, cue in enumerate(cues):
        ms = cue_to_ms(cue, fps)
        if ms is None:
            continue
        delay = ms - anchor_offset
        if delay < 0:
            print(
                f"  ⚠️  cue '{cue}' ({ms}ms) < anchor offset ({anchor_offset}ms); "
                f"clamping to 0 — sfx midpoint will land later than cue"
            )
            delay = 0
        filter_parts.append(f"[0:a]adelay={delay}|{delay}[a{i}]")
        inputs_count += 1
    if inputs_count == 0:
        return None, 0
    mix_labels = "".join([f"[a{i}]" for i in range(inputs_count)])
    mix = (
        ";".join(filter_parts)
        + f";{mix_labels}amix=inputs={inputs_count}:dropout_transition=0:normalize=0[mix]"
    )
    return mix, inputs_count


def parse_loudnorm_json(stderr_text):
    # loudnorm prints a JSON block at the end of stderr
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr_text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def main(config_file, lufs, tp, lra, fps, anchor_pct):
    if not os.path.exists(config_file):
        print(f"File {config_file} not found.")
        return

    with open(config_file, "r") as f:
        lines = [
            line.strip()
            for line in f.readlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    if len(lines) < 3:
        print(
            "Error: The text file must contain at least: input file, one cue, and output file."
        )
        return

    input_mp3 = lines[0]
    output_wav = lines[-1]
    cues = lines[1:-1]

    sfx_ms = get_audio_duration_ms(input_mp3)
    if sfx_ms is None:
        print(f"Could not probe duration of {input_mp3}.")
        return
    anchor_offset = round((anchor_pct / 100.0) * sfx_ms)
    print(
        f"SFX: {input_mp3} ({sfx_ms} ms) | anchor {anchor_pct}% = {anchor_offset} ms "
        f"(cues shifted back by this amount so the anchor lands on the marker)"
    )

    mix, inputs_count = build_mix_filter(cues, fps, anchor_pct, sfx_ms)
    if mix is None:
        print("No valid cues found.")
        return

    loudnorm_base = f"loudnorm=I={lufs}:TP={tp}:LRA={lra}"

    # --- Pass 1: measure ---
    pass1_filter = f"{mix};[mix]{loudnorm_base}:print_format=json[out]"
    pass1_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        input_mp3,
        "-filter_complex",
        pass1_filter,
        "-map",
        "[out]",
        "-f",
        "null",
        "-",
    ]
    print(f"Pass 1: measuring loudness (target {lufs} LUFS)...")
    result = subprocess.run(pass1_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Pass 1 failed:")
        print(result.stderr)
        return

    measured = parse_loudnorm_json(result.stderr)
    if not measured:
        print("Could not parse loudnorm measurements from pass 1.")
        print(result.stderr)
        return

    print(
        f"  measured I={measured['input_i']} LUFS, TP={measured['input_tp']} dBTP, "
        f"LRA={measured['input_lra']} LU"
    )

    # --- Pass 2: apply with measured values ---
    pass2_loudnorm = (
        f"{loudnorm_base}"
        f":measured_I={measured['input_i']}"
        f":measured_TP={measured['input_tp']}"
        f":measured_LRA={measured['input_lra']}"
        f":measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}"
        f":linear=true:print_format=summary"
    )
    pass2_filter = f"{mix};[mix]{pass2_loudnorm},aresample=48000[out]"
    pass2_cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        input_mp3,
        "-filter_complex",
        pass2_filter,
        "-map",
        "[out]",
        output_wav,
    ]
    print(f"Pass 2: normalizing and writing {output_wav}...")
    subprocess.run(pass2_cmd)
    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mix an mp3 at given cues (timestamps or frame numbers) and loudness-normalize (two-pass)."
    )
    parser.add_argument("config_file", help="Text file: input, cues..., output (cues are HH:MM:SS.mmm or integer frame numbers)")
    parser.add_argument(
        "--lufs", type=float, default=-15.0, help="Integrated loudness target (default: -15)"
    )
    parser.add_argument(
        "--tp", type=float, default=-1.5, help="True-peak ceiling in dBTP (default: -1.5)"
    )
    parser.add_argument(
        "--lra", type=float, default=11.0, help="Loudness range target in LU (default: 11)"
    )
    parser.add_argument(
        "--fps", type=float, default=24.0, help="Frames per second for frame-number cues (default: 24)"
    )
    parser.add_argument(
        "--anchor", type=float, default=50.0,
        help="Percentage into the sfx file that should land on the cue marker: "
             "0=beginning, 50=middle (default), 100=end",
    )
    args = parser.parse_args()
    if not 0 <= args.anchor <= 100:
        parser.error("--anchor must be between 0 and 100")
    main(args.config_file, args.lufs, args.tp, args.lra, args.fps, args.anchor)
