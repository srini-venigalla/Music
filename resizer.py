import subprocess
import sys
import os

def parse_kv_args(args):
    params = {"x": "0", "y": "0"}
    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.lower().strip()
            if key in params:
                params[key] = value.strip()
    return params

def process_video(input_file, mode, x="0", y="0"):
    file_name, file_ext = os.path.splitext(input_file)
    
    # Helper to only add X/Y to filename if they aren't 0
    def get_name_part(val, label):
        try:
            if float(val) != 0: return f"_{label}{val}"
        except ValueError: return f"_{label}custom"
        return ""

    xname = get_name_part(x, 'x')
    yname = get_name_part(y, 'y')
    output_file = f"{file_name}_169_{mode}{yname}{xname}{file_ext}"

    # Filter Setup
    zoom_filter = f"crop=iw:iw*9/16:{x}:{y},scale=trunc(iw/2)*2:trunc(ih/2)*2"
    modes = {
        "zoom": zoom_filter,
        "pad": "pad=ih*16/9:ih:(ow-iw)/2:(oh-ih)/2",
        "blur": "split[v1][v2];[v1]scale=ih*16/9:-1,boxblur=20:10[bg];[v2]scale=-1:ih[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,crop=ih*16/9:ih"
    }

    cmd = ['ffmpeg', '-i', input_file, '-vf', modes[mode]]
    if file_ext.lower() in ['.png', '.jpg', '.jpeg']:
        cmd += ['-vframes', '1'] 
    else:
        cmd += ['-c:a', 'copy']
    cmd += ['-y', output_file]

    try:
        print(f"--- 🎥 Processing {mode.upper()} | Y={y} X={x} ---")
        subprocess.run(cmd, check=True)
        print(f"✅ Created: {output_file}")
    except subprocess.CalledProcessError:
        print("❌ Error: Check your coordinates.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 resizer.py <file> zoom y=100")
    else:
        f_name = sys.argv[1]
        m_type = sys.argv[2].lower()
        kv = parse_kv_args(sys.argv[3:])
        process_video(f_name, m_type, kv["x"], kv["y"])