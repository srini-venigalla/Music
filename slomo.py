import subprocess
import argparse
import sys

def slow_video(input_file, output_file, factor, mute=False):
    """
    factor > 1.0 makes it SLOWER (takes more time).
    factor < 1.0 makes it FASTER (takes less time).
    """
    
    # Video Filter: setpts
    video_filter = f"setpts={factor}*PTS"
    
    # Audio Logic
    if mute:
        audio_args = ["-an"] # Strip audio
        filter_str = f"[0:v]{video_filter}[v]"
        map_args = ["-map", "[v]"]
    else:
        # atempo is the reciprocal of the PTS factor
        # Example: factor 2.0 (slower) means tempo 0.5
        atempo_val = 1.0 / factor
        
        # atempo chain for extreme slowness (below 0.5)
        parts = []
        temp_tempo = atempo_val
        while temp_tempo < 0.5:
            parts.append("atempo=0.5")
            temp_tempo /= 0.5
        parts.append(f"atempo={temp_tempo}")
        audio_filter = ",".join(parts)
        
        filter_str = f"[0:v]{video_filter}[v];[0:a]{audio_filter}[a]"
        map_args = ["-map", "[v]", "-map", "[a]"]

    command = [
        'ffmpeg',
        '-i', input_file,
        '-filter_complex', filter_str,
    ] + map_args + ['-y', output_file]

    try:
        print(f"--- Processing: {input_file} ---")
        print(f"--- Duration Multiplier: {factor}x ---")
        subprocess.run(command, check=True)
        print(f"--- Done: {output_file} ---")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg Error: {e}", file=sys.stderr)
    except FileNotFoundError:
        print("Error: FFmpeg is not installed.", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Change video speed using FFmpeg.")
    parser.add_argument("input", help="Input file")
    parser.add_argument("output", help="Output file")
    parser.add_argument("-f", "--factor", type=float, default=2.0, 
                        help="Slowing factor. >1 is slower, <1 is faster. (Default 2.0)")
    parser.add_argument("-n", "--no-audio", action="store_true", help="Remove audio from the output")

    args = parser.parse_args()
    slow_video(args.input, args.output, args.factor, args.no_audio)
    