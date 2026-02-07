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
        except:
            return 5.0

    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(filename)}"
    try:
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        total_dur = float(output)
        def to_sec(t):
            if not t: return None
            parts = t.split(':')
            return sum(float(x) * 60**i for i, x in enumerate(reversed(parts)))
        s = to_sec(start_time) or 0.0
        e = to_sec(end_time) or total_dur
        return e - s
    except:
        return 5.0

def parse_line(line):
    line = line.strip()
    matches = list(re.finditer(r'\s(\d{1,2}:[\d:.]+|\d+\.\d+|\d+:\d+)', line))
    if not matches: return line, None, None
    filename = line[:matches[0].start()].strip()
    timestamps = [m.group().strip() for m in matches]
    return filename, timestamps[0], (timestamps[1] if len(timestamps) > 1 else None)

def generate_workflow(input_file):
    base_name = os.path.splitext(input_file)[0]
    interim_dir = tempfile.mkdtemp(prefix="stitch_")
    concat_file = os.path.join(interim_dir, "list.txt")
    interim_video = f"{base_name}_stitched.mp4"
    audio_bg = f"{base_name}.mp3"
    final_output = f"{base_name}_video.mp4"

    video_configs = []
    with open(input_file, 'r') as f:
        for line in f:
            if not line.strip(): continue
            fname, start, end = parse_line(line)
            if os.path.exists(fname):
                video_configs.append({'file': fname, 'start': start, 'end': end})

    processed_files = []
    print(f"🛠️ Phase 1: Normalizing {len(video_configs)} items...")

    for i, cfg in enumerate(video_configs):
        ext = os.path.splitext(cfg['file'])[1].lower()
        is_img = ext in ['.jpg', '.jpeg', '.png', '.webp']
        out_ts = os.path.join(interim_dir, f"clip_{i:03d}.ts")
        dur = get_duration(cfg['file'], cfg['start'], cfg['end'])

        if is_img:
            # Process Image to Video Clip
            cmd = (f"ffmpeg -y -loop 1 -t {dur} -i {shlex.quote(cfg['file'])} "
                   f"-f lavfi -i anullsrc=r=48000:cl=stereo -t {dur} "
                   f"-vf \"scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p\" "
                   f"-c:v libx264 -preset superfast -c:a aac -shortest {out_ts}")
        else:
            # Process Video Segment
            ss = f"-ss {cfg['start']}" if cfg['start'] else ""
            to = f"-to {cfg['end']}" if cfg['end'] else ""
            cmd = (f"ffmpeg -y {ss} {to} -i {shlex.quote(cfg['file'])} "
                   f"-vf \"scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p\" "
                   f"-c:v libx264 -preset superfast -c:a aac -ar 48000 -ac 2 {out_ts}")
        
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processed_files.append(out_ts)
        print(f"  [{i+1}/{len(video_configs)}] Processed {os.path.basename(cfg['file'])}")

    with open(concat_file, 'w') as f:
        for p in processed_files:
            f.write(f"file '{p}'\n")

    print(f"\n🔗 Phase 2: Stitching clips...")
    stitch_cmd = f"ffmpeg -y -f concat -safe 0 -i {concat_file} -c copy {interim_video}"
    subprocess.run(stitch_cmd, shell=True)

    if os.path.exists(audio_bg):
        print(f"\n🎵 Phase 3: Applying background audio...")
        final_cmd = (f"ffmpeg -y -i {interim_video} -i {shlex.quote(audio_bg)} "
                     f"-map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest {final_output}")
        subprocess.run(final_cmd, shell=True)
    
    print(f"\n✅ Done! Created: {final_output}")

if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python3 makevideo.py project.txt")
    else: generate_workflow(sys.argv[1])
    