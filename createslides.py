import os
import sys
import argparse
import textwrap
from PIL import Image, ImageDraw, ImageFont

def generate_lyrics_images(input_file, basename, font_path, font_size, bg_color, text_color):
    output_dir = "generated_lyrics"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # utf-8 is essential for Telugu script support
        with open(input_file, 'r', encoding='utf-8') as f:
            sections = [s.strip() for s in f.read().split('<--->') if s.strip()]
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found.")
        return

    img_size = (1080, 1080)
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"❌ Font Error: Could not find '{font_path}'.")
        print("Please make sure the .ttf file is in the same folder as this script.")
        return

    print(f"🚀 Processing {len(sections)} Telugu sections...")

    for i, text in enumerate(sections, 1):
        img = Image.new('RGB', img_size, color=bg_color)
        draw = ImageDraw.Draw(img)

        # Telugu characters are visually dense; 25-30 chars per line is usually the sweet spot
        wrapper = textwrap.TextWrapper(width=30) 
        wrapped_text = "\n".join([wrapper.fill(line) for line in text.splitlines()])

        # Calculate centering with spacing for 'vattulu' and 'maatras'
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center", spacing=20)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        position = ((img_size[0] - text_w) / 2, (img_size[1] - text_h) / 2)

        # Draw text with complex shaping enabled for correct stacking
        draw.multiline_text(
            position, 
            wrapped_text, 
            fill=text_color, 
            font=font, 
            align="center", 
            spacing=20,
            features=["rakm"] 
        )

        out_name = f"{basename}_{i:02d}.png"
        img.save(os.path.join(output_dir, out_name))
        print(f"   [+] Generated: {out_name}")

    print(f"\n✨ Done! Your images are in the '{output_dir}' folder.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Beautiful Telugu Lyric Image Generator")
    
    # Show help if no input file is provided
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Required positional argument
    parser.add_argument("file", help="Path to your .txt file with <---> delimiters")
    
    # Updated Defaults per your request
    parser.add_argument("--font", default="AnekTelugu-Regular.ttf", help="Default: AnekTelugu-Regular.ttf")
    parser.add_argument("--size", type=int, default=70, help="Default: 70")
    parser.add_argument("--name", default="telugu_lyric", help="Basename for output files")
    parser.add_argument("--bg", default="#121212", help="Background hex")
    parser.add_argument("--text", default="#FFFFFF", help="Text hex")

    args = parser.parse_args()
    generate_lyrics_images(args.file, args.name, args.font, args.size, args.bg, args.text)