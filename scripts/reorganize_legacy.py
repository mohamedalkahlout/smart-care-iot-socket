#!/usr/bin/env python3
"""
Legacy Files Migration Script
Reorganizes legacy academic POC files into legacy/academic_poc/
"""
import os
import shutil

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
legacy_poc = os.path.join(repo_root, "legacy", "academic_poc")

os.makedirs(os.path.join(legacy_poc, "wokwi_simulation"), exist_ok=True)
os.makedirs(os.path.join(legacy_poc, "documents"), exist_ok=True)
os.makedirs(os.path.join(legacy_poc, "prototypes"), exist_ok=True)

# 1. Move root documents
docs_to_move = [
    "Presentation_SmartSocket_EN.pptx",
    "Smart_IoT_Socket_Project_Report_M_AlKahlout.pdf"
]
for d in docs_to_move:
    src = os.path.join(repo_root, d)
    if os.path.exists(src):
        dst = os.path.join(legacy_poc, "documents", d)
        print(f"Moving doc {d} -> legacy/academic_poc/documents/")
        shutil.move(src, dst)

# 2. Move root Wokwi directory
wokwi_root = os.path.join(repo_root, "Wokwi")
if os.path.exists(wokwi_root):
    print("Moving root Wokwi directory contents into legacy/academic_poc/wokwi_simulation/")
    for item in os.listdir(wokwi_root):
        s = os.path.join(wokwi_root, item)
        d = os.path.join(legacy_poc, "wokwi_simulation", item)
        if os.path.exists(d):
            if os.path.isdir(d):
                shutil.rmtree(d)
            else:
                os.remove(d)
        shutil.move(s, d)
    shutil.rmtree(wokwi_root, ignore_errors=True)

# Also check legacy/Wokwi if present
legacy_old_wokwi = os.path.join(repo_root, "legacy", "Wokwi")
if os.path.exists(legacy_old_wokwi):
    shutil.rmtree(legacy_old_wokwi, ignore_errors=True)

# 3. Move Arabic prototype folders into prototypes/
proto_folders = [
    ("المشروع الأساسي", "initial_base"),
    ("المشروع التجريبي", "experimental_poc"),
    ("المشروع الكبير", "extended_poc"),
    ("نظام المقابس الذكية المتكامل", "integrated_archive")
]

for src_name, target_sub in proto_folders:
    src = os.path.join(repo_root, src_name)
    dst = os.path.join(legacy_poc, "prototypes", target_sub)
    if os.path.exists(src):
        print(f"Moving {src_name} -> legacy/academic_poc/prototypes/{target_sub}")
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.move(src, dst)

# Also clean up legacy/المشروع الأساسي and legacy/المشروع التجريبي if left over
for old_sub in ["المشروع الأساسي", "المشروع التجريبي"]:
    p = os.path.join(repo_root, "legacy", old_sub)
    if os.path.exists(p):
        shutil.rmtree(p, ignore_errors=True)

# Move المقبس الذكي.rar
rar_file = os.path.join(repo_root, "المقبس الذكي.rar")
if os.path.exists(rar_file):
    shutil.move(rar_file, os.path.join(legacy_poc, "prototypes", "المقبس الذكي.rar"))

# Move vsix if present to legacy/prototypes
vsix = os.path.join(repo_root, "GitHub.vscode-github-actions-0.32.3.vsix")
if os.path.exists(vsix):
    shutil.move(vsix, os.path.join(legacy_poc, "prototypes", "GitHub.vscode-github-actions-0.32.3.vsix"))

print("Migration completed successfully.")
