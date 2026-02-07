import subprocess
import os
import sys
import shlex

def get_duration(filename):
    """Uses ffprobe to get the duration of a video file."""
    # Use shlex.quote for the filename to handle spaces and parentheses
    quoted_name = shlex.quote(filename)
    cmd = (
        f"ffprobe -v error -show_entries format=duration "
        f"-of default=noprint_wrappers=1:nokey=1 {quoted_name}"
    )
    try:
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        return float(output)
    except Exception as e:
        print(f"Error probing {filename}: {e}")
        sys.exit(1)

def generate_workflow(input_file):
    # --- NAMING CONVENTION LOGIC ---
    base_name = os.path.splitext(input_file)[0]
    audio_file = f"{base_name}.mp3"
    interim_video = f"{base_name}.mp4"
    final_output = f"{base_name}_video.mp4"
    
    TRANSITION_DURATION = 1.5

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    with open(input_file, 'r') as f:
        # Clean up filenames and handle potential empty lines
        videos = [line.strip() for line in f if line.strip()]

    if len(videos) < 2:
        print("Error: You need at least two videos in the list to stitch.")
        sys.exit(1)

    print(f"🔍 Probing {len(videos)} clips for durations...")
    durations = [get_duration(v) for v in videos]
    
    # 1. Build Scaling and Audio Pre-processing chain
    filter_parts = []
    for i in range(len(videos)):
        filter_parts.append(f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,setsar=1/1,format=yuv420p[v{i}]")
        filter_parts.append(f"[{i}:a]aresample=48000[a{i}]")

    # 2. Build xfade/acrossfade logic
    current_v_out = "v0"
    current_a_out = "a0"
    cumulative_offset = 0.0

    for i in range(1, len(videos)):
        # Calculate offset: (Total duration of previous clips) - (Overlap from transitions)
        cumulative_offset += durations[i-1] - TRANSITION_DURATION
        
        # Video transition
        next_v_out = f"vt{i}" if i < len(videos) - 1 else "finalv"
        filter_parts.append(f"[{current_v_out}][v{i}]xfade=transition=fade:duration={TRANSITION_DURATION}:offset={cumulative_offset:.2f}[{next_v_out}]")
        current_v_out = next_v_out
        
        # Audio transition
        next_a_out = f"at{i}" if i < len(videos) - 1 else "finala"
        filter_parts.append(f"[{current_a_out}][a{i}]acrossfade=d={TRANSITION_DURATION}[{next_a_out}]")
        current_a_out = next_a_out

    full_filter = " ; ".join(filter_parts)
    
    # Properly quote every input file for the shell
    inputs_str = " ".join([f"-i {shlex.quote(v)}" for v in videos])

    # --- STEP 1: STITCHING ---
    stitch_cmd = (
        f"ffmpeg -y {inputs_str} -filter_complex \"{full_filter}\" "
        f"-map \"[finalv]\" -map \"[finala]\" -pix_fmt yuv420p "
        f"-c:v libx264 -crf 18 -c:a aac -b:a 192k {shlex.quote(interim_video)}"
    )

    print(f"\n🎬 Step 1: Stitching clips into {interim_video}...")
    result = subprocess.run(stitch_cmd, shell=True)

    if result.returncode != 0:
        print("\n❌ Error: Step 1 failed. FFmpeg could not stitch the videos.")
        sys.exit(1)

    # --- STEP 2: AUDIO OVERLAY ---
    if os.path.exists(audio_file):
        overlay_cmd = (
            f"ffmpeg -y -stream_loop -1 -i {shlex.quote(interim_video)} -i {shlex.quote(audio_file)} "
            f"-map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest {shlex.quote(final_output)}"
        )
        print(f"\n🎵 Step 2: Overlaying audio from {audio_file}...")
        overlay_result = subprocess.run(overlay_cmd, shell=True)
        
        if overlay_result.returncode == 0:
            print(f"\n✅ SUCCESS: Final video created: {final_output}")
        else:
            print("\n❌ Error: Step 2 failed during audio overlay.")
    else:
        print(f"\n⚠️  Note: {audio_file} not found. Skipping Step 2.")
        print(f"Stitched video (no overlay) is at: {interim_video}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 makevideo.py <project_name>.txt")
    else:
        generate_workflow(sys.argv[1])
