#!/usr/bin/env python3
"""
Convert portrait (vertical) videos to 16:9 landscape with blurred side areas using FFmpeg.
Preserves 100% of the original content (no cropping of main video).
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Convert portrait videos to 16:9 with blurred background sides.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input video file or directory (for batch processing)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output video file (single mode) or output directory (batch mode)",
    )

    # Core parameters
    parser.add_argument(
        "--blur-type",
        choices=["gblur", "boxblur"],
        default="gblur",
        help="Blur filter to use: gblur (Gaussian) or boxblur",
    )
    parser.add_argument(
        "--blur-strength",
        type=float,
        default=20.0,
        help="Blur intensity. For gblur: sigma value (10-40). For boxblur: radius factor.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1920,
        help="Output width in pixels (height will be calculated to maintain 16:9)",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="Constant Rate Factor for quality (lower = better quality, larger file; 17-23 recommended)",
    )
    parser.add_argument(
        "--preset",
        default="medium",
        choices=[
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
        ],
        help="FFmpeg encoding preset (trade-off between speed and compression)",
    )

    # Optional refinements
    parser.add_argument(
        "--dim-background",
        type=float,
        default=0.0,
        help="Dim the blurred background (0.0 = no change, -0.3 = noticeably darker)",
    )
    parser.add_argument(
        "--force-1080p",
        action="store_true",
        help="Force output to exactly 1920x1080 regardless of input height",
    )
    parser.add_argument(
        "--hwaccel",
        action="store_true",
        help="Enable hardware acceleration (auto-detect, faster on supported GPUs)",
    )
    parser.add_argument(
        "--overwrite",
        "-y",
        action="store_true",
        help="Overwrite output file without asking",
    )

    # Batch mode
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all video files in the input directory",
    )
    parser.add_argument(
        "--extensions",
        default="mp4,mov,avi,mkv",
        help="Comma-separated list of extensions to process in batch mode",
    )

    args = parser.parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path '{input_path}' does not exist.")
        sys.exit(1)

    # Build FFmpeg filter
    if args.blur_type == "gblur":
        blur_filter = f"gblur=sigma={args.blur_strength}"
    else:  # boxblur
        blur_filter = f"boxblur=luma_radius=min(h\\,w)/20:luma_power=1:chroma_radius=min(cw\\,ch)/20:chroma_power=1"

    # Optional background dimming
    if args.dim_background != 0.0:
        eq_filter = f",eq=brightness={args.dim_background}"
    else:
        eq_filter = ""

    # Core filter chain (highly optimized version)
    filter_complex = (
        f"split[original][copy];"
        f"[copy]scale=ih*{args.width}/1080:-1,crop=h=iw*9/16,{blur_filter}{eq_filter}[blurred];"
        f"[blurred][original]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    )
    

    if args.force_1080p:
        filter_complex += ",scale=1920:1080"

    # Build base FFmpeg command
    cmd_base = ["ffmpeg"]
    if args.hwaccel:
        cmd_base.extend(["-hwaccel", "auto"])
    if args.overwrite:
        cmd_base.append("-y")

    # Single file mode
    if not args.batch:
        if not input_path.is_file():
            print("Error: For single mode, --input must be a file.")
            sys.exit(1)

        output_path = (
            Path(args.output)
            if args.output
            else input_path.with_stem(input_path.stem + "_16x9")
        )
        if output_path.suffix == "":
            output_path = output_path.with_suffix(".mp4")

        cmd = cmd_base + [
            "-i",
            str(input_path),
            "-vf",
            filter_complex,
            "-c:v",
            "libx264",
            "-crf",
            str(args.crf),
            "-preset",
            args.preset,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        print(f"Processing: {input_path.name} → {output_path.name}")
        print(
            f"Blur: {args.blur_type} (strength {args.blur_strength}), CRF: {args.crf}, Preset: {args.preset}"
        )

        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Done: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg error: {e}")
            sys.exit(1)

    # Batch mode
    else:
        if not input_path.is_dir():
            print("Error: For batch mode, --input must be a directory.")
            sys.exit(1)

        output_dir = Path(args.output) if args.output else input_path / "16x9_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        ext_list = [e.strip().lower() for e in args.extensions.split(",")]

        video_files = []
        for ext in ext_list:
            video_files.extend(input_path.glob(f"*.{ext}"))
            video_files.extend(input_path.glob(f"*.{ext.upper()}"))

        if not video_files:
            print("No video files found in the input directory.")
            sys.exit(1)

        print(f"Found {len(video_files)} video files. Starting batch processing...\n")

        for idx, video in enumerate(video_files, 1):
            output_path = output_dir / (video.stem + "_16x9" + video.suffix)

            cmd = cmd_base + [
                "-i",
                str(video),
                "-vf",
                filter_complex,
                "-c:v",
                "libx264",
                "-crf",
                str(args.crf),
                "-preset",
                args.preset,
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                str(output_path),
            ]

            print(f"[{idx}/{len(video_files)}] Processing: {video.name}")
            try:
                subprocess.run(
                    cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                print(f"   ✅ {output_path.name}")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Failed: {video.name} - {e.stderr.decode()[:200]}...")

        print(f"\n✅ Batch processing complete! Files saved to: {output_dir}")


if __name__ == "__main__":
    main()
