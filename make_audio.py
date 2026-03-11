import sys
import os
from pydub import AudioSegment

def parse_time_to_ms(time_str):
    try:
        time_str = time_str.replace("..", ".").replace(",", ".").rstrip('.')
        if "." in time_str:
            parts = time_str.split(".")
            ms = int(parts[1].ljust(3, "0")[:3])
            base_time = parts[0]
        else:
            base_time = time_str
            ms = 0
        parts = list(map(int, base_time.split(":")))
        if len(parts) == 3: h, m, s = parts
        elif len(parts) == 2: h, m, s = 0, parts[0], parts[1]
        else: h, m, s = 0, 0, parts[0]
        return (h * 3600000) + (m * 60000) + (s * 1000) + ms
    except: return None

def main():
    # Use command line args if provided
    input_manifest = sys.argv[1] if len(sys.argv) > 1 else "audio_extend.txt"
    output_filename = sys.argv[2] if len(sys.argv) > 2 else "combined_output.mp3"
    
    print(f"--- Starting Audio Merger ---")
    print(f"Manifest: {input_manifest}")
    print(f"Output:   {output_filename}\n")

    if not os.path.exists(input_manifest):
        print(f"Error: Manifest file '{input_manifest}' not found.")
        return

    combined_audio = AudioSegment.empty()
    crossfade_ms = 50 

    with open(input_manifest, "r") as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"): continue

        # Handle filenames with spaces by splitting carefully
        parts = line.split()
        if not parts: continue
        
        filename = parts[0]
        start_t = parts[1] if len(parts) > 1 else "0"
        end_t = parts[2] if len(parts) > 2 else None

        if not os.path.exists(filename):
            print(f"Line {line_num}: File '{filename}' NOT FOUND. Skipping.")
            continue

        try:
            start_ms = parse_time_to_ms(start_t)
            # Handle the 'end' keyword or timestamp
            if end_t and end_t.lower() == 'end':
                end_ms = None
            else:
                end_ms = parse_time_to_ms(end_t) if end_t else None

            # from_file handles MP3 and WAV
            audio = AudioSegment.from_file(filename)
            
            if end_ms:
                segment = audio[start_ms:end_ms]
            else:
                segment = audio[start_ms:]

            print(f"Processed: {filename} ({len(segment)}ms)")

            if len(combined_audio) > 0:
                combined_audio = combined_audio.append(segment, crossfade=crossfade_ms)
            else:
                combined_audio = segment
        except Exception as e:
            print(f"Error on line {line_num}: {e}")

    if len(combined_audio) > 0:
        print(f"\nExporting final file...")
        combined_audio.export(output_filename, format="mp3", bitrate="320k")
        print(f"SUCCESS: {output_filename} created.")
    else:
        print("FAILED: No audio segments were processed.")

if __name__ == "__main__":
    main()