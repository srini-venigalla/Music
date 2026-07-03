import subprocess
import argparse
import os
import sys

def merge_versions(input1, input2, output, vol1=1.0, vol2=1.0):
    """
    Merges two audio tracks by overlapping them for 
    comparative analysis or hybrid production.
    """
    if not os.path.exists(input1) or not os.path.exists(input2):
        print(f"Error: Could not find {input1} or {input2}")
        return

    # FFmpeg filter complex to mix audio and align durations
    filter_cmd = (
        f"[0:a]volume={vol1}[a1]; "
        f"[1:a]volume={vol2},highpass=f=200[a2]; "
        f"[a1][a2]amix=inputs=2:duration=longest"
    )

    cmd = [
        'ffmpeg', '-y',
        '-i', input1,
        '-i', input2,
        '-filter_complex', filter_cmd,
        '-ac', '2',
        output
    ]

    try:
        print(f"Blending {input1} and {input2}...")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        print(f"Successfully generated hybrid track: {output}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during merging: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tushar-Leena Project: Version Merger Utility",
        epilog="Example: python3 vmerge.py track1.mp3 track2.mp3 -v1 1.2 -o master.mp3"
    )
    parser.add_argument("file1", nargs='?', help="Primary audio version")
    parser.add_argument("file2", nargs='?', help="Secondary audio version")
    parser.add_argument("-o", "--output", default="merged_comparison.mp3", help="Output filename")
    parser.add_argument("-v1", "--vol1", type=float, default=1.0, help="Volume for primary file")
    parser.add_argument("-v2", "--vol2", type=float, default=1.0, help="Volume for secondary file")

    # Show help and exit if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    # Ensure positional arguments are present if we got past the length check
    if not args.file1 or not args.file2:
        print("Error: Two input files are required.")
        parser.print_usage()
        sys.exit(1)

    merge_versions(args.file1, args.file2, args.output, args.vol1, args.vol2)