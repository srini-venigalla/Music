import subprocess
import argparse


def to_seconds(timestr):
    """Converts HH:MM:SS.ms or MM:SS.ms to total seconds."""
    if ":" not in timestr:
        return float(timestr)
    parts = [float(p) for p in timestr.split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def main():
    parser = argparse.ArgumentParser(
        description="Extract a segment from an mp4 file."
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-s", "--start", required=True, help="Start time (HH:MM:SS.ms or seconds)")
    parser.add_argument("-d", "--duration", required=True, help="Duration (HH:MM:SS.ms or seconds)")
    parser.add_argument("-o", "--output", required=True)

    args = parser.parse_args()

    start = to_seconds(args.start)
    duration = to_seconds(args.duration)

    command = [
        "ffmpeg",
        "-ss",
        str(start),
        "-i",
        args.input,
        "-t",
        str(duration),
        "-preset",
        "ultrafast",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        args.output,
        "-y",
    ]

    print(f"--- Extracting {duration}s starting at {start}s ---")
    try:
        subprocess.run(command, check=True)
        print(f"\nSuccess! Saved to {args.output}")
    except subprocess.CalledProcessError as err:
        print(f"Error: {err}")


if __name__ == "__main__":
    main()
