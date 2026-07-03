import subprocess
import argparse
import os
import sys
import re

def get_smart_breaks(filename, noise_val=20, duration="0.2", verbose=False):
    """Analyzes audio for phrase endings using inverted dB logic."""
    noise_str = f"-{abs(noise_val)}dB"
    cmd = [
        'ffmpeg', '-i', filename,
        '-af', f'silencedetect=n={noise_str}:d={duration}',
        '-f', 'null', '-'
    ]
    
    if verbose:
        print(f"Internal Noise Threshold: {noise_str}")
    
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    return [float(p) for p in re.findall(r"silence_start: ([\d\.]+)", result.stderr)]

def compare_weave(input1, input2, output, noise_val=20, duration="0.1", verbose=False):
    if not os.path.exists(input1) or not os.path.exists(input2):
        print("Error: Input files not found.")
        return

    print(f"Analyzing {input1} for comparison points (-{abs(noise_val)}dB)...")
    breaks = get_smart_breaks(input1, noise_val, duration, verbose)
    
    def get_duration(f):
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', f]
        return float(subprocess.check_output(cmd).strip())
    
    total_duration = get_duration(input1)
    if not breaks or breaks[-1] < total_duration - 0.5:
        breaks.append(total_duration)

    segment_files = []
    current_time = 0.0
    
    try:
        for i, break_point in enumerate(breaks):
            seg_len = break_point - current_time
            if seg_len < 0.1: continue
            
            # The "Double-Time" Logic: Grab the segment from BOTH inputs
            for track_idx, input_file in enumerate([input1, input2]):
                # Distinguish files so we don't overwrite during the loop
                seg_name = os.path.abspath(f"comp_seg_{i}_t{track_idx}.mp3")
                
                cmd = [
                    'ffmpeg', '-y', '-ss', str(current_time), '-t', str(seg_len),
                    '-i', input_file, '-acodec', 'libmp3lame', '-b:a', '192k',
                    seg_name
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                segment_files.append(seg_name)
            
            # Move the timeline forward only after both tracks are sampled
            current_time = break_point

        # Build the Manifest
        manifest_path = os.path.abspath("compare_manifest.txt")
        with open(manifest_path, "w") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        print(f"Stitching {len(segment_files)} segments for sequential A/B comparison...")
        concat_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', manifest_path, '-c', 'copy', output
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(output):
            print(f"SUCCESS: Comparison track created: {output}")
            print(f"Total phrases compared: {len(breaks)}")

    finally:
        if not verbose:
            for seg in segment_files:
                if os.path.exists(seg): os.remove(seg)
            if os.path.exists("compare_manifest.txt"): os.remove("compare_manifest.txt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tushar-Leena Project: Side-by-Side Audio Weaver")
    parser.add_argument("file1", help="Primary song version")
    parser.add_argument("file2", help="Secondary song version")
    parser.add_argument("-n", "--noise", type=int, default=20, help="Positive dB (e.g. 20)")
    parser.add_argument("-d", "--duration", default="0.1", help="Silence duration")
    parser.add_argument("-o", "--output", default="comparison_master.mp3")
    parser.add_argument("-v", "--verbose", action="store_true")
    
    args = parser.parse_args()
    compare_weave(args.file1, args.file2, args.output, args.noise, args.duration, args.verbose)