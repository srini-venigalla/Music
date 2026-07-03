#!/usr/bin/env python3
"""Expand `X N` markers in an SFX timestamp file into N timestamps offset by a few ms.

Input file format:
    line 1        : sfx wav file
    middle lines  : HH:MM:SS.fff timestamps, optionally suffixed with "X N"
    last line     : timeline track

Usage:
    python blip_blop.py anklets1.txt                 # edit in place, .bak saved
    python blip_blop.py anklets1.txt -o out.txt      # write to new file
    python blip_blop.py anklets1.txt --offset-ms 40  # custom spacing
"""
import argparse
import re
import shutil
from pathlib import Path

MARKER_RE = re.compile(r'^(\d+):(\d+):(\d+)\.(\d+)\s+X\s+(\d+)\s*$')


def to_ms(h, m, s, frac):
    ms = int(frac.ljust(3, '0')[:3])
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + ms


def fmt_ms(total_ms):
    h, rem = divmod(total_ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def expand(lines, offset_ms):
    out = []
    for line in lines:
        m = MARKER_RE.match(line.strip())
        if not m:
            out.append(line)
            continue
        h, mn, s, frac, n = m.groups()
        base = to_ms(h, mn, s, frac)
        for i in range(int(n)):
            out.append(fmt_ms(base + i * offset_ms))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('input', help='SFX timestamp file')
    ap.add_argument('-o', '--output', help='output path (default: overwrite input)')
    ap.add_argument('--offset-ms', type=int, default=50,
                    help='spacing between bloops in ms (default: 50)')
    ap.add_argument('--no-backup', action='store_true',
                    help='skip writing <input>.bak when editing in place')
    args = ap.parse_args()

    src = Path(args.input)
    lines = src.read_text().splitlines()
    new_lines = expand(lines, args.offset_ms)

    dest = Path(args.output) if args.output else src
    if dest == src and not args.no_backup:
        shutil.copy2(src, src.with_suffix(src.suffix + '.bak'))
    dest.write_text('\n'.join(new_lines) + '\n')
    print(f"wrote {dest} ({len(new_lines)} lines, was {len(lines)})")


if __name__ == '__main__':
    main()
