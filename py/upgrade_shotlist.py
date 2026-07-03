#!/usr/bin/env python3
"""Upgrade each .mp4 filename in a shot list to its highest available HitPaw variant.

Priority (highest first): wie > wi > w > i4 > ii > i > original
Skips subdirectory paths (anything containing /) and non-mp4 files.
Backs up <input> as <input>.bak before rewriting.
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

PRIORITY = ["wie", "wi", "w", "i4", "ii", "i"]


def build_dir_index(directory):
    """Return {lower_name: actual_name} for *.mp4 in directory."""
    return {e.name.lower(): e.name for e in os.scandir(directory) if e.is_file()}


def upgrade(name, index):
    p = Path(name)
    if p.suffix.lower() != ".mp4" or "/" in name:
        return name
    m = re.match(r"^(?P<base>.+?)_(?P<code>wie|wi|w|i4|ii|i)\d*$", p.stem)
    if m:
        base = m.group("base")
        current_idx = PRIORITY.index(m.group("code"))
    else:
        base = p.stem
        current_idx = len(PRIORITY)
    for i, code in enumerate(PRIORITY):
        if i >= current_idx:
            break
        candidate = f"{base}_{code}.mp4".lower()
        if candidate in index:
            return index[candidate]
    return name


def main():
    ap = argparse.ArgumentParser(description="Upgrade shot list filenames to highest HitPaw variant")
    ap.add_argument("shotlist", help="Path to shot list .txt")
    ap.add_argument("--dir", help="Directory to search (default: shot list's dir)")
    args = ap.parse_args()

    shotlist = Path(args.shotlist)
    search_dir = Path(args.dir) if args.dir else shotlist.parent
    index = build_dir_index(search_dir)

    backup = shotlist.with_suffix(shotlist.suffix + ".bak")
    shutil.copy2(shotlist, backup)
    print(f"Backed up to {backup}\n")

    out_lines = []
    changes = 0
    with open(shotlist, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            m = re.match(r"^(\s*)(\S+)(.*)$", stripped)
            if not m:
                out_lines.append(line)
                continue
            leading, first_tok, rest = m.groups()
            new_tok = upgrade(first_tok, index)
            if new_tok != first_tok:
                out_lines.append(f"{leading}{new_tok}{rest}\n")
                print(f"  {first_tok} → {new_tok}")
                changes += 1
            else:
                out_lines.append(line)

    with open(shotlist, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    print(f"\n✅ Upgraded {changes} lines")


if __name__ == "__main__":
    main()
