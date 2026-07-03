import argparse
import os
import sys
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range


def process_stems(v_path, i_path, out_path):
    print(f"--- Technical Check ---")
    print(f"Vocal Path: {os.path.abspath(v_path)}")
    print(f"Instrument Path: {os.path.abspath(i_path)}")

    try:
        print("Loading Vocal Stem...")
        vocal = AudioSegment.from_file(v_path)
        print(f"Loaded Vocals: {len(vocal) / 1000:.2f} seconds")

        print("Loading Instrument Stem...")
        instrument = AudioSegment.from_file(i_path)
        print(f"Loaded Instruments: {len(instrument) / 1000:.2f} seconds")

        print("Applying Leveler to Vocals...")
        vocal = compress_dynamic_range(vocal, threshold=-24.0, ratio=4.0)
        vocal = vocal.low_pass_filter(11000)

        print("Merging Stems...")
        # Ensure we don't lose volume during overlay
        final_mix = instrument.overlay(vocal)
        final_mix = normalize(final_mix, headroom=1.5)

        print(f"Exporting to: {out_path}...")
        final_mix.export(out_path, format="wav")

        if os.path.exists(out_path):
            print(f"✅ SUCCESS! File created: {os.path.abspath(out_path)}")
            print(f"File size: {os.path.getsize(out_path) / 1024 / 1024:.2f} MB")
        else:
            print(
                "❌ ERROR: Export finished but file is missing. Check FFmpeg permissions."
            )

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Stem Mixer")
    parser.add_argument("-v", "--vocal", required=True)
    parser.add_argument("-i", "--instrument", required=True)
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    if not os.path.exists(args.vocal):
        print(f"❌ Cannot find vocal file: {args.vocal}")
        return
    if not os.path.exists(args.instrument):
        print(f"❌ Cannot find instrument file: {args.instrument}")
        return

    process_stems(args.vocal, args.instrument, args.output)


if __name__ == "__main__":
    main()
