import os
import sys
import argparse
import textwrap
import re
from PIL import Image, ImageDraw, ImageFont


def generate_lyrics_images(
    input_file, basename, font_path, font_size, bg_input, text_color,
    stroke_width, stroke_color, canvas_size, vh, hh,
):
    def format_color(c):
        if re.match(r"^[0-9a-fA-F]{6}$", c):
            return f"#{c}"
        return c

    text_color = format_color(text_color)
    stroke_color = format_color(stroke_color)
    output_dir = "generated_lyrics"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    dynamic_spacing = int(font_size * 0.618)

    bg_cache = {}

    def resolve_bg(bg):
        if bg in bg_cache:
            return bg_cache[bg]
        if os.path.isfile(bg):
            try:
                img = Image.open(bg).convert("RGB")
                resolved = ("image", img, img.size)
                print(f"🖼️ Loaded background '{bg}': {img.size[0]}x{img.size[1]}")
            except Exception as e:
                print(f"⚠️ Error loading background '{bg}': {e}")
                resolved = ("color", format_color(bg), (1080, 1080))
        else:
            resolved = ("color", format_color(bg), (1080, 1080))
        bg_cache[bg] = resolved
        return resolved

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found.")
        return

    pattern = re.compile(r"<--(.+?)-->|<--->|\[.*?\]")
    sections = []
    last_end = 0
    current_bg = bg_input
    for m in pattern.finditer(content):
        text = content[last_end:m.start()].strip()
        if text:
            sections.append((current_bg, text))
        if m.group(1) is not None:
            current_bg = m.group(1).strip()
        last_end = m.end()
    tail = content[last_end:].strip()
    if tail:
        sections.append((current_bg, tail))

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        print(f"❌ Font Error: Could not find '{font_path}'.")
        return

    print(f"🚀 Processing {len(sections)} sections with spacing: {dynamic_spacing}px")

    vh_clamped = max(0.0, min(1.0, vh))
    hh_clamped = max(0.0, min(1.0, hh))

    def fit_cover(src, target):
        tw, th = target
        iw, ih = src.size
        scale = max(tw / iw, th / ih)
        new_w, new_h = int(round(iw * scale)), int(round(ih * scale))
        resized = src.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - tw) // 2
        top = (new_h - th) // 2
        return resized.crop((left, top, left + tw, top + th))

    for i, (bg, text) in enumerate(sections, 1):
        mode, value, _ = resolve_bg(bg)
        if mode == "image":
            img = fit_cover(value, canvas_size)
        else:
            img = Image.new("RGB", canvas_size, color=value)
        img_size = canvas_size
        draw = ImageDraw.Draw(img)

        # Wrap text - width 30 is standard, but you can adjust based on image width
        wrapper = textwrap.TextWrapper(width=30)
        wrapped_text = "\n".join([wrapper.fill(line) for line in text.splitlines()])

        # Calculate bounding box using our dynamic spacing
        bbox = draw.multiline_textbbox(
            (0, 0), wrapped_text, font=font, align="center", spacing=dynamic_spacing,
            stroke_width=stroke_width,
        )
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        position = ((img_size[0] - text_w) * hh_clamped, (img_size[1] - text_h) * vh_clamped)

        draw.multiline_text(
            position,
            wrapped_text,
            fill=text_color,
            font=font,
            align="center",
            spacing=dynamic_spacing,
            features=["rakm"],
            stroke_width=stroke_width,
            stroke_fill=stroke_color,
        )

        out_name = f"{basename}_{i:02d}.png"
        img.save(os.path.join(output_dir, out_name))
        print(f"   [+] Generated: {out_name} (bg: {bg})")

    print(f"\n✨ Done! Check the '{output_dir}' folder.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telugu Lyric Image Generator")
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    parser.add_argument("file", help="Path to your .txt file")
    parser.add_argument("--font", default="AnekTelugu-Regular.ttf")
    parser.add_argument("--size", type=int, default=70)
    parser.add_argument("--name", default="telugu_lyric")
    parser.add_argument("--bg", default="121212", help="Background PNG or Hex code")
    parser.add_argument("--color", default="FFFFFF", help="Text Hex code")
    parser.add_argument("--stroke", type=int, default=3, help="Stroke (outline) width in px; 0 disables")
    parser.add_argument("--stroke-color", default="000000", help="Stroke Hex code")
    parser.add_argument("--canvas", default="1080x1080", help="Output size as WIDTHxHEIGHT (e.g. 1920x1080)")
    parser.add_argument("--vh", type=float, default=0.5, help="Vertical text anchor on canvas: 0.0=top, 0.5=center, 1.0=bottom")
    parser.add_argument("--hh", type=float, default=0.5, help="Horizontal text anchor on canvas: 0.0=left, 0.5=center, 1.0=right")

    args = parser.parse_args()
    try:
        cw, ch = args.canvas.lower().split("x")
        canvas_size = (int(cw), int(ch))
    except Exception:
        print(f"❌ Invalid --canvas '{args.canvas}'. Use WIDTHxHEIGHT, e.g. 1920x1080.")
        sys.exit(1)

    generate_lyrics_images(
        args.file, args.name, args.font, args.size, args.bg, args.color,
        args.stroke, args.stroke_color, canvas_size, args.vh, args.hh,
    )
