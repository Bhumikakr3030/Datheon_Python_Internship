#!/usr/bin/env python3
"""organizer.py - Sort a cluttered directory (e.g. Downloads) into category folders.

Usage:
    python organizer.py                      # organizes ~/Downloads
    python organizer.py /path/to/folder      # organizes a specific folder
    python organizer.py --dry-run            # preview without moving anything
"""

import argparse
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

# extension -> category folder
EXTENSION_MAP = {
    # Documents
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
    ".txt": "Documents", ".rtf": "Documents", ".odt": "Documents",
    ".xls": "Documents", ".xlsx": "Documents", ".csv": "Documents",
    ".ppt": "Documents", ".pptx": "Documents", ".md": "Documents",
    ".epub": "Documents",
    # Images
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
    ".bmp": "Images", ".webp": "Images", ".svg": "Images", ".tiff": "Images",
    ".heic": "Images",
    # Videos
    ".mp4": "Videos", ".mkv": "Videos", ".mov": "Videos", ".avi": "Videos",
    ".wmv": "Videos", ".flv": "Videos", ".webm": "Videos",
    # Archives
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives",
    ".tar": "Archives", ".gz": "Archives", ".bz2": "Archives", ".xz": "Archives",
    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".html": "Code",
    ".css": "Code", ".java": "Code", ".c": "Code", ".cpp": "Code",
    ".h": "Code", ".go": "Code", ".rs": "Code", ".sh": "Code",
    ".json": "Code", ".yaml": "Code", ".yml": "Code", ".sql": "Code",
    ".ipynb": "Code",
}

# Files that are likely still downloading / temporary: never touch these.
SKIP_EXTENSIONS = {".crdownload", ".part", ".partial", ".tmp", ".download"}


def unique_destination(dest_dir: Path, name: str) -> Path:
    """Return a path in dest_dir that doesn't exist yet: 'file.pdf' -> 'file (1).pdf'."""
    candidate = dest_dir / name
    if not candidate.exists():
        return candidate
    stem, suffix = Path(name).stem, Path(name).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def organize(target: Path, dry_run: bool = False) -> dict:
    stats = {"moved": Counter(), "skipped": 0, "renamed": 0, "errors": []}
    self_path = Path(__file__).resolve()

    try:
        entries = list(os.scandir(target))
    except PermissionError:
        print(f"Error: no permission to read {target}", file=sys.stderr)
        sys.exit(1)

    for entry in entries:
        # Only regular files; leave folders and symlinks alone.
        if not entry.is_file(follow_symlinks=False):
            continue

        src = Path(entry.path)
        if src.resolve() == self_path:
            continue

        ext = src.suffix.lower()
        category = EXTENSION_MAP.get(ext)
        if ext in SKIP_EXTENSIONS or category is None:
            stats["skipped"] += 1
            continue

        dest_dir = target / category
        try:
            if not dry_run:
                dest_dir.mkdir(exist_ok=True)
            dest = unique_destination(dest_dir, src.name)
            if dest.name != src.name:
                stats["renamed"] += 1

            if dry_run:
                print(f"[dry-run] {src.name} -> {category}/{dest.name}")
            else:
                shutil.move(str(src), str(dest))
            stats["moved"][category] += 1
        except PermissionError:
            stats["errors"].append(f"{src.name}: permission denied (file may be open or read-only)")
        except FileExistsError:
            stats["errors"].append(f"{src.name}: destination already exists")
        except OSError as exc:
            stats["errors"].append(f"{src.name}: {exc}")

    return stats


def print_summary(target: Path, stats: dict, dry_run: bool) -> None:
    total = sum(stats["moved"].values())
    verb = "Would move" if dry_run else "Moved"
    line = "=" * 44
    print(f"\n{line}\n  ORGANIZER SUMMARY{' (DRY RUN)' if dry_run else ''}\n{line}")
    print(f"  Folder : {target}")
    print(f"  {verb:<7}: {total} file(s)")
    for category, count in sorted(stats["moved"].items()):
        print(f"    - {category:<10} {count}")
    print(f"  Renamed to avoid collision : {stats['renamed']}")
    print(f"  Skipped (unknown/temp)     : {stats['skipped']}")
    print(f"  Errors                     : {len(stats['errors'])}")
    for err in stats["errors"]:
        print(f"    ! {err}")
    print(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Organize files into category folders by extension.")
    parser.add_argument("directory", nargs="?", default=str(Path.home() / "Downloads"),
                        help="folder to organize (default: ~/Downloads)")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="show what would happen without moving anything")
    args = parser.parse_args()

    target = Path(args.directory).expanduser().resolve()
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        sys.exit(1)

    stats = organize(target, args.dry_run)
    print_summary(target, stats, args.dry_run)


if __name__ == "__main__":
    main()
