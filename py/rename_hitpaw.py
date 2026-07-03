#!/usr/bin/env python3
"""Shorten HitPaw-processed mp4 filenames.

Mapping
  w   = AI Watermark Removal
  wi  = w + Frame Interpolated Model(X2)
  wie = wi + General/UHD Restoration Model
  i   = Frame Interpolated Model(X2) only (no watermark step)
  ii  = double Frame Interpolated Model(X2)
  i4  = Frame Interpolated Model(X4)

A `(N)` marker anywhere in the original filename is appended as a digit
(e.g. _wi1, _wie1) so re-runs don't collide.

Default is a dry run; pass --apply to actually rename.
"""
import argparse
import os
import re
import sys
from pathlib import Path


PATTERNS = [
    (re.compile(
        r"^(?P<base>.+?)"
        r"_AI Watermark Removal_\d+x\d+(?:\((?P<n1>\d+)\))?"
        r"_Frame Interpolated Model\(X2\)_\d+x\d+(?:\((?P<n2>\d+)\))?"
        r"_(?:General|UHD) Restoration Model_\d+x\d+(?:\((?P<n3>\d+)\))?"
        r"\.mp4$"), "wie"),
    (re.compile(
        r"^(?P<base>.+?)"
        r"_AI Watermark Removal_\d+x\d+(?:\((?P<n1>\d+)\))?"
        r"_Frame Interpolated Model\(X2\)_\d+x\d+(?:\((?P<n2>\d+)\))?"
        r"\.mp4$"), "wi"),
    (re.compile(
        r"^(?P<base>.+?)"
        r"_AI Watermark Removal_\d+x\d+(?:\((?P<n1>\d+)\))?"
        r"\.mp4$"), "w"),
    (re.compile(
        r"^(?P<base>.+?)"
        r"_Frame Interpolated Model\(X2\)_\d+x\d+(?:\((?P<n1>\d+)\))?"
        r"_Frame Interpolated Model\(X2\)_\d+x\d+(?:\((?P<n2>\d+)\))?"
        r"\.mp4$"), "ii"),
    (re.compile(
        r"^(?P<base>.+?)"
        r"_Frame Interpolated Model\(X4\)_\d+x\d+(?:\((?P<n1>\d+)\))?"
        r"\.mp4$"), "i4"),
    (re.compile(
        r"^(?P<base>.+?)"
        r"_Frame Interpolated Model\(X2\)_\d+x\d+(?:\((?P<n1>\d+)\))?"
        r"\.mp4$"), "i"),
]


def proposed_name(filename):
    for rx, code in PATTERNS:
        m = rx.match(filename)
        if not m:
            continue
        base = m.group("base")
        nums = [m.group(g) for g in m.groupdict() if g.startswith("n") and m.group(g)]
        suffix = max(nums) if nums else ""
        return f"{base}_{code}{suffix}.mp4"
    return None


def main():
    ap = argparse.ArgumentParser(description="Shorten HitPaw mp4 filenames")
    ap.add_argument("dir", help="Directory containing the .mp4 files")
    ap.add_argument("--apply", action="store_true", help="Actually rename (default: dry run)")
    args = ap.parse_args()

    d = Path(args.dir)
    plan = []
    for f in sorted(d.iterdir()):
        if not f.is_file() or f.suffix != ".mp4":
            continue
        new = proposed_name(f.name)
        if new and new != f.name:
            plan.append((f.name, new))

    targets = {}
    for old, new in plan:
        targets.setdefault(new, []).append(old)
    collisions = {t: olds for t, olds in targets.items() if len(olds) > 1}

    print(f"Found {len(plan)} files matching HitPaw patterns")
    for old, new in plan:
        marker = " ⚠ COLLISION" if new in collisions else ""
        print(f"  {old}\n    → {new}{marker}")

    existing = [(o, n) for o, n in plan if (d / n).exists() and (d / n).resolve() != (d / o).resolve()]
    problems = collisions or existing

    if existing:
        print("\nTarget filename already exists on disk:")
        for o, n in existing:
            print(f"  {o} → {n}")

    if collisions:
        print("\nMultiple sources map to the same target:")
        for t, olds in collisions.items():
            print(f"  {t} ← {olds}")

    if args.apply:
        if problems:
            print("\nAborting --apply due to problems above.")
            sys.exit(1)
        for old, new in plan:
            (d / old).rename(d / new)
        print(f"\n✅ Renamed {len(plan)} files")
    else:
        print("\n(dry run — pass --apply to perform the rename)")


if __name__ == "__main__":
    main()
