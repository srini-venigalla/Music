import sys
import os
from pydub import AudioSegment

def parse_time_to_ms(time_str):
    """
    Converts various timestamp formats to milliseconds.
    Supports: HH:MM:SS.mmm, HH:MM:SS, MM:SS.mmm, etc.
    """
    try:
        # Standardize decimal separator and remove trailing dots
        time_str = time_str.replace("..", ".").replace(",", ".").rstrip('.')

        if "." in time_str:
            base_time, ms_part = time_str.split(".")
            # Ensure ms is exactly 3 digits (e.g., .1 -> 100, .1234 -> 123)
            ms = int(ms_part.ljust(3, "0")[:3])
        else:
            base_time = time_str
            ms = 0

        parts = list(map(int, base_time.split(":")))

        if len(parts) == 3:    # HH:MM:SS
            h, m, s = parts
        elif len(parts) == 2:  # MM:SS
            h, m, s = 0, parts[0], parts[1]
        elif len(parts) == 1:  # SS
            h, m, s = 0, 0, parts[0]
        else:
            return None

        return (h * 3600000) + (m * 60000) + (s * 1000) + ms
    except Exception:
        return None

def process_line(line):
    """
    Improved splitting: Finds the first token ending in a known audio extension.
    Everything after that token is a timestamp.
    """
    tokens = line.strip().split()
    if not tokens:
        return None, 0, None

    filename = ""
    timestamps = []
    
    # Common audio extensions to look for
    extensions = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')

    # Find the index of the token that looks like the filename
    file_token_index = -1
    for i, token in enumerate(tokens):
        if token.lower().endswith(extensions):
            file_token_index = i
            break
    
    if file_token_index != -1:
        # Filename is everything up to and including the extension token
        filename = " ".join(tokens[:file_token_index + 1])
        timestamps = tokens[file_token_index + 1:]
    else:
        # Fallback to old logic if no extension found
        filename = tokens[0]
        timestamps = tokens[1:]

    start_ms = 0
    end_ms = None

    if len(timestamps) >= 1:
        val = parse_time_to_ms(timestamps[0])
        if val is not None:
            start_ms = val

    if len(timestamps) >= 2:
        val = parse_time_to_ms(timestamps[1])
        if val is not None:
            end_ms = val

    return filename, start_ms, end_ms

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 make_audio.py <input_list.txt> <output_filename.mp3>")
        sys.exit(1)

    input_list_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_list_file):
        print(f"Error: List file '{input_list_file}' not found.")
        sys.exit(1)

    combined_audio = AudioSegment.empty()
    files_processed = 0

    print(f"--- Processing: {input_list_file} ---")

    with open(input_list_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            filename, start_ms, end_ms = process_line(line)

            if not os.path.exists(filename):
                print(f"Line {line_num}: Warning - File '{filename}' not found. Skipping.")
                continue

            try:
                print(f"Loading: {filename.ljust(20)}", end=" ", flush=True)
                audio_segment = AudioSegment.from_mp3(filename)
                duration = len(audio_segment)

                # Slicing logic
                if end_ms is not None:
                    # Ensure we don't try to cut past the end of the file
                    end_ms = min(end_ms, duration)
                    segment = audio_segment[start_ms:end_ms]
                    print(f"[{start_ms}ms -> {end_ms}ms]")
                elif start_ms > 0:
                    segment = audio_segment[start_ms:]
                    print(f"[{start_ms}ms -> End]")
                else:
                    segment = audio_segment
                    print("[Full Track]")

                combined_audio += segment
                files_processed += 1

            except Exception as e:
                print(f"\nError processing line {line_num} ({filename}): {e}")

    if files_processed > 0:
        print(f"\nExporting combined audio ({len(combined_audio)}ms) to '{output_file}'...")
        combined_audio.export(output_file, format="mp3")
        print("Done!")
    else:
        print("\nNo audio segments were successfully merged.")

if __name__ == "__main__":
    main()