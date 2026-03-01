import os
import random
import argparse
from pydub import AudioSegment, silence, effects

def process_raga_medley(folder_path, silence_limit, threshold, crossfade_ms):
    # Use current directory if '.' is passed
    target_dir = os.path.abspath(folder_path)
    files = sorted([f for f in os.listdir(target_dir) if f.endswith('.mp3')])
    
    if not files:
        print(f"Error: No MP3 files found in '{target_dir}'")
        return

    final_composition = AudioSegment.silent(duration=0)
    history = []

    print(f"--- Raga Mixer CLI ---")
    print(f"Settings: Threshold={threshold}dB, Min Silence={silence_limit}ms, Crossfade={crossfade_ms}ms")
    print(f"Analyzing {len(files)} files...\n")

    for file_name in files:
        file_path = os.path.join(target_dir, file_name)
        audio = AudioSegment.from_file(file_path)
        
        # Split logic
        segments = silence.split_on_silence(
            audio, 
            min_silence_len=silence_limit, 
            silence_thresh=threshold,
            keep_silence=300
        )
        
        if not segments:
            print(f"  [!] {file_name}: No segments found. Using full track.")
            chosen_segment = audio
            label = "Full Track"
        else:
            print(f"  [✓] {file_name}: Found {len(segments)} segments.")
            idx = random.randint(0, len(segments) - 1)
            chosen_segment = segments[idx]
            label = f"Segment {idx + 1}"

        chosen_segment = effects.normalize(chosen_segment)
        
        if len(final_composition) > 0:
            final_composition = final_composition.append(chosen_segment, crossfade=crossfade_ms)
        else:
            final_composition = chosen_segment
            
        history.append(f"{file_name} -> {label}")

    out_file = "random_raga_medley.mp3"
    final_composition.export(out_file, format="mp3", bitrate="192k")
    
    with open("mixer_log.txt", "w") as log:
        log.write("\n".join(history))

    print(f"\nSUCCESS: Created {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mix ragas based on silence detection.")
    parser.add_argument("path", nargs='?', default=".", help="Folder containing MP3s (default: current)")
    parser.add_argument("--thresh", type=int, default=-25, help="Silence threshold in dB (default: -25)")
    parser.add_argument("--dur", type=int, default=500, help="Min silence duration in ms (default: 500)")
    parser.add_argument("--fade", type=int, default=1000, help="Crossfade between tracks in ms (default: 1000)")

    args = parser.parse_args()
    process_raga_medley(args.path, args.dur, args.thresh, args.fade)