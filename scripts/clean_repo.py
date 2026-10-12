#!/usr/bin/env python3
"""
Repository Sanitization & Hygiene Script
Smart Care IoT Socket (Retrofit Edge-AI & Safety Guard)

Performs comprehensive cleanup of:
1. PlatformIO build artifacts (firmware/.pio/)
2. Python bytecode caches (__pycache__/, *.pyc, *.pyo)
3. OS metadata and hidden artifacts (.DS_Store, Thumbs.db)
"""

import os
import shutil
import sys

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def clean_repository(repo_root: str):
    print("=" * 70)
    print("🧹 [HYGIENE] Starting Repository Deep Clean & Sanitization")
    print(f"    Target Directory: {repo_root}")
    print("=" * 70)

    removed_dirs = 0
    removed_files = 0
    reclaimed_bytes = 0

    # 1. Target firmware/.pio specifically
    pio_dir = os.path.join(repo_root, "firmware", ".pio")
    if os.path.exists(pio_dir):
        print(f"[*] Removing PlatformIO build directory: {pio_dir}")
        for root, dirs, files in os.walk(pio_dir, topdown=False):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    reclaimed_bytes += os.path.getsize(fp)
                    os.remove(fp)
                    removed_files += 1
                except Exception as e:
                    print(f"    [!] Failed to remove file {fp}: {e}")
        try:
            shutil.rmtree(pio_dir)
            removed_dirs += 1
            print("    [✓] firmware/.pio removed successfully.")
        except Exception as e:
            print(f"    [!] Failed to remove dir {pio_dir}: {e}")

    # 2. Walk entire repository to clean cache, pyc, and OS files
    for root, dirs, files in os.walk(repo_root, topdown=False):
        # Skip .git directory
        if ".git" in root.split(os.sep):
            continue

        # Files cleanup
        for file_name in files:
            file_lower = file_name.lower()
            file_path = os.path.join(root, file_name)

            should_delete = False
            if file_lower in [".ds_store", "thumbs.db", "ehthumbs.db"]:
                should_delete = True
            elif file_lower.endswith((".pyc", ".pyo", ".pyd")):
                should_delete = True
            elif file_name.startswith("._"):
                should_delete = True

            if should_delete:
                try:
                    reclaimed_bytes += os.path.getsize(file_path)
                    os.remove(file_path)
                    removed_files += 1
                except Exception as e:
                    print(f"    [!] Failed to remove {file_path}: {e}")

        # Directories cleanup (__pycache__, .pytest_cache)
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if dir_name in ["__pycache__", ".pytest_cache"]:
                try:
                    shutil.rmtree(dir_path)
                    removed_dirs += 1
                except Exception as e:
                    print(f"    [!] Failed to remove directory {dir_path}: {e}")

    mb_freed = reclaimed_bytes / (1024 * 1024)
    print("-" * 70)
    print("✨ [SUMMARY] Repository Sanitization Completed:")
    print(f"    - Directories removed: {removed_dirs}")
    print(f"    - Files removed:       {removed_files}")
    print(f"    - Disk space freed:    {mb_freed:.2f} MB")
    print("=" * 70)


if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    clean_repository(repo_root)
