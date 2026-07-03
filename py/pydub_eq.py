import argparse
import os
import sys
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

def apply_room_reverb(audio, wet_level=0.15):
    """
    Simulates a grand French room by layering multiple micro-delays.
    Corrected to use pydub's segment addition for delays.
    """
    from pydub import AudioSegment
    
    # Create the 'wet' layers (delayed versions of the audio)
    # We create silence of 40ms and 75ms to offset the audio
    delay_1_ms = 40
    delay_2_ms = 75
    
    # Delay 1: Low pass at 2.5kHz + 40ms silence at start
    delay_1 = AudioSegment.silent(duration=delay_1_ms) + audio.low_pass_filter(2500)
    # Delay 2: Low pass at 2.0kHz + 75ms silence at start
    delay_2 = AudioSegment.silent(duration=delay_2_ms) + audio.low_pass_filter(2000)
    
    # Overlay them back onto the original audio
    # -12dB and -15dB keeps the echoes from being too loud
    reverb_tail = (delay_1 - 12).overlay(delay_2 - 15)
    
    # Mix with the original 'dry' audio
    return audio.overlay(reverb_tail, gain_during_overlay=wet_level)

def apply_slow_duet_preset(audio):
    """FOUNDATION: EQ + Compression"""
    print("Applying 'slow_duet' foundation...")
    audio = audio.high_pass_filter(80)
    presence = audio.high_pass_filter(3000).low_pass_filter(5000)
    audio = audio.overlay(presence + 3.5)
    audio = compress_dynamic_range(audio, threshold=-18.0, ratio=3.0)
    return normalize(audio, headroom=1.0)

def apply_french_room_preset(audio):
    """ATMOSPHERE: Reverb"""
    print("Applying 'french_room' atmosphere...")
    audio = apply_room_reverb(audio, wet_level=0.18)
    return normalize(audio, headroom=1.0)

def main():
    parser = argparse.ArgumentParser(description="pydub_eq: Pro Audio Presets")
    parser.add_argument("-preset", choices=["slow_duet", "french_room"], required=True)
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=True)

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        sys.exit(1)

    audio = AudioSegment.from_file(args.input)

    if args.preset == "slow_duet":
        audio = apply_slow_duet_preset(audio)
    elif args.preset == "french_room":
        audio = apply_french_room_preset(audio)

    ext = args.output.split('.')[-1]
    audio.export(args.output, format=ext)
    print(f"✅ Exported to {args.output}")

if __name__ == "__main__":
    main()