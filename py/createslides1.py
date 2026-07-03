import os
import sys
import argparse
import textwrap
import re  # Added for pattern matching
from PIL import Image, ImageDraw, ImageFont


def generate_lyrics_images(
    input_file, basename, font_path, font_size, bg_color, text_color
):
    output_dir = "generated_lyrics"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

            # This regex splits by <---> OR any [Text] pattern
            # The pattern r'<--->|\[.*?\]' looks for exactly those two things
            sections = re.split(r"<--->|\[.*?\]", content)

            # Remove empty strings and strip whitespace from each section
            sections = [s.strip() for s in sections if s.strip()]

    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found.")
        return

    img_size = (1080, 1080)

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        print(f"❌ Font Error: Could not find '{font_path}'.")
        return

    print(f"🚀 Processing {len(sections)} Telugu sections...")

    for i, text in enumerate(sections, 1):
        img = Image.new("RGB", img_size, color=bg_color)
        draw = ImageDraw.Draw(img)

        wrapper = textwrap.TextWrapper(width=30)
        wrapped_text = "\n".join([wrapper.fill(line) for line in text.splitlines()])

        # Calculate centering
        bbox = draw.multiline_textbbox(
            (0, 0), wrapped_text, font=font, align="center", spacing=20
        )
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        position = ((img_size[0] - text_w) / 2, (img_size[1] - text_h) / 2)

        draw.multiline_text(
            position,
            wrapped_text,
            fill=text_color,
            font=font,
            align="center",
            spacing=20,
            features=["rakm"],
        )

        out_name = f"{basename}_{i:02d}.png"
        img.save(os.path.join(output_dir, out_name))
        print(f"   [+] Generated: {out_name}")

    print(f"\n✨ Done! Your images are in the '{output_dir}' folder.")


# ... (rest of your argparse code remains the same)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Beautiful Telugu Lyric Image Generator"
    )
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    parser.add_argument("file", help="Path to your .txt file")
    parser.add_argument("--font", default="AnekTelugu-Regular.ttf")
    parser.add_argument("--size", type=int, default=70)
    parser.add_argument("--name", default="telugu_lyric")
    parser.add_argument("--bg", default="#121212")
    parser.add_argument("--text", default="#FFFFFF")

    args = parser.parse_args()
    generate_lyrics_images(
        args.file, args.name, args.font, args.size, args.bg, args.text
    )
