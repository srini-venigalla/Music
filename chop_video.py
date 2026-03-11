import subprocess
import argparse
import sys


def to_seconds(timestr):
    """Converts HH:MM:SS.ms or MM:SS.ms to total seconds."""
    if ":" not in timestr:
        return float(timestr)
    parts = timestr.split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 3:  # HH:MM:SS
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:  # MM:SS
        return parts[0] * 60 + parts[1]
    return parts[0]


def main():
    parser = argparse.ArgumentParser(
        description="Precision removal of a video segment."
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-s", "--junk_start", required=True)
    parser.add_argument("-e", "--junk_end", required=True)
    parser.add_argument("-o", "--output", required=True)

    args = parser.parse_args()

    # Convert timestamps to raw seconds for the filter
    s = to_seconds(args.junk_start)
    e = to_seconds(args.junk_end)

    # The Logic:
    # 1. Trim video/audio to 's'
    # 2. Trim video/audio from 'e' to end
    # 3. Reset timestamps (setpts) so they join seamlessly
    filter_cmd = (
        f"[0:v]trim=end={s},setpts=PTS-STARTPTS[v1]; "
        f"[0:v]trim=start={e},setpts=PTS-STARTPTS[v2]; "
        f"[0:a]atrim=end={s},asetpts=PTS-STARTPTS[a1]; "
        f"[0:a]atrim=start={e},asetpts=PTS-STARTPTS[a2]; "
        f"[v1][a1][v2][a2]concat=n=2:v=1:a=1[outv][outa]"
    )

    command = [
        "ffmpeg",
        "-i",
        args.input,
        "-filter_complex",
        filter_cmd,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-preset",
        "ultrafast",
        "-c:v",
        "libx264",  # Explicitly using a standard codec
        "-c:a",
        "aac",  # Explicitly using a standard audio codec
        args.output,
        "-y",
    ]

    print(f"--- Slicing out the junk: {s}s to {e}s ---")
    try:
        subprocess.run(command, check=True)
        print(f"\nSuccess! Saved to {args.output}")
    except subprocess.CalledProcessError as err:
        print(f"Error: {err}")


if __name__ == "__main__":
    main()
