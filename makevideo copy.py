import subprocess
import os
import sys
import shlex
import re
import tempfile

def get_duration(filename, start_time=None, end_time=None):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.webp']:
        try:
            return float(start_time) if start_time else 5.0
        except (ValueError, TypeError):
            return 5.0

    quoted_name = shlex.quote(filename)
    cmd = (
        f"ffprobe -v error -show_entries format=duration "
        f"-of default=noprint_wrappers=1:nokey=1 {quoted_name}"
    )
    try:
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        total_dur = float(output)
        
        def to_sec(t):
            if not t: return None
            parts = t.split(':')
            if len(parts) == 1: return float(parts[0])
            return sum(float(x) * 60**i for i, x in enumerate(reversed(parts)))

        s = to_sec(start_time) or 0.0
        e = to_sec(end_time) or total_dur
        return e - s
    except Exception:
        print(f"❌ Could not find or probe file: {filename}")
        sys.exit(1)

def parse_line(line):
    line = line.strip()
    matches = list(re.finditer(r'\s(\d{1,2}:[\d:.]+|\d+\.\d+|\d+:\d+)', line))
    if not matches:
        return line, None, None
    
    first_match_start = matches[0].start()
    filename = line[:first_match_start].strip()
    timestamps = [m.group().strip() for m in matches]
    start = timestamps[0] if len(timestamps) > 0 else None
    end = timestamps[1] if len(timestamps) > 1 else None
    
    return filename, start, end

def generate_workflow(input_file):
    base_name = os.path.splitext(input_file)[0]
    audio_file = f"{base_name}.mp3"
    interim_video = f"{base_name}.mp4"
    final_output = f"{base_name}_video.mp4"
    
    TRANSITION_DURATION = 1.5
    FADE_EFFECT_DURATION = 1.0 

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    video_configs = []
    with open(input_file, 'r') as f:
        for line in f:
            if not line.strip(): continue
            fname, start, end = parse_line(line)
            if os.path.exists(fname):
                video_configs.append({'file': fname, 'start': start, 'end': end})
            else:
                print(f"⚠️ Warning: File not found: {fname}")

    print(f"🔍 Probing {len(video_configs)} items...")
    durations = [get_duration(cfg['file'], cfg['start'], cfg['end']) for cfg in video_configs]
    
    total_sequence_duration = sum(durations) - (len(durations) - 1) * TRANSITION_DURATION
    
    input_list = []
    filter_parts = []
    
    # Input 0: Dummy Audio
    input_list.append("-f lavfi -i anullsrc=r=48000:cl=stereo")

    for i, cfg in enumerate(video_configs):
        ext = os.path.splitext(cfg['file'])[1].lower()
        is_image = ext in ['.jpg', '.jpeg', '.png', '.webp']
        
        # input_idx is i + 1 because input 0 is anullsrc
        input_idx = i + 1
        v_label = f"v{i}"
        
        if is_image:
            dur = durations[i]
            input_list.append(f"-loop 1 -t {dur} -i {shlex.quote(cfg['file'])}")
            filter_parts.append(f"[{input_idx}:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,setsar=1/1,format=yuv420p[{v_label}_pre]")
            # For images, we just use the global Input 0 (silent audio)
            filter_parts.append(f"[0:a]atrim=duration={dur},asetpts=PTS-STARTPTS[a{i}]")
        else:
            start_arg = f"-ss {cfg['start']} " if cfg['start'] else ""
            end_arg = f"-to {cfg['end']} " if cfg['end'] else ""
            input_list.append(f"{start_arg}{end_arg}-i {shlex.quote(cfg['file'])}")
            filter_parts.append(f"[{input_idx}:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,setsar=1/1,format=yuv420p[{v_label}_pre]")
            filter_parts.append(f"[{input_idx}:a]aresample=48000[a{i}]")

        if i == 0:
            filter_parts.append(f"[{v_label}_pre]fade=t=in:st=0:d={FADE_EFFECT_DURATION}[{v_label}]")
        else:
            filter_parts.append(f"[{v_label}_pre]copy[{v_label}]")

    # XFade / Acrossfade Logic
    current_v_out, current_a_out = "v0", "a0"
    cumulative_offset = 0.0
    for i in range(1, len(video_configs)):
        cumulative_offset += durations[i-1] - TRANSITION_DURATION
        next_v_out = f"vt{i}" if i < len(video_configs) - 1 else "stitched_v"
        filter_parts.append(f"[{current_v_out}][v{i}]xfade=transition=fade:duration={TRANSITION_DURATION}:offset={cumulative_offset:.2f}[{next_v_out}]")
        current_v_out = next_v_out
        
        next_a_out = f"at{i}" if i < len(video_configs) - 1 else "stitched_a"
        filter_parts.append(f"[{current_a_out}][a{i}]acrossfade=d={TRANSITION_DURATION}[{next_a_out}]")
        current_a_out = next_a_out

    # Final Fade Out
    fade_out_start = total_sequence_duration - FADE_EFFECT_DURATION
    filter_parts.append(f"[{current_v_out}]fade=t=out:st={fade_out_start:.2f}:d={FADE_EFFECT_DURATION}[finalv]")

    # Create a temporary filter file to avoid command-line length limits
    with tempfile.NamedTemporaryFile(mode='w', suffix='.filter', delete=False) as tf:
        tf.write(" ; ".join(filter_parts))
        filter_path = tf.name

    inputs_str = " ".join(input_list)
    stitch_cmd = (
        f"ffmpeg -y {inputs_str} -filter_complex_script {shlex.quote(filter_path)} "
        f"-map \"[finalv]\" -map \"[stitched_a]\" -pix_fmt yuv420p "
        f"-c:v libx264 -crf 18 -c:a aac -b:a 192k {shlex.quote(interim_video)}"
    )

    print(f"\n🎬 Step 1: Stitching {len(video_configs)} items...")
    result = subprocess.run(stitch_cmd, shell=True)
    os.remove(filter_path)

    if result.returncode == 0 and os.path.exists(audio_file):
        overlay_cmd = (
            f"ffmpeg -y -stream_loop -1 -i {shlex.quote(interim_video)} -i {shlex.quote(audio_file)} "
            f"-map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest {shlex.quote(final_output)}"
        )
        print(f"\n🎵 Step 2: Audio Overlay...")
        subprocess.run(overlay_cmd, shell=True)
        print(f"\n✅ COMPLETE: {final_output}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 makevideo.py <project>.txt")
    else:
        generate_workflow(sys.argv[1])