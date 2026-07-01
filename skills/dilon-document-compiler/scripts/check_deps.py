"""Preflight dependency check for the dilon-document-compiler skill."""

import importlib
import shutil
import subprocess
import sys

REQUIRED_MODULES = ["docx", "docxtpl", "docxcompose", "yaml"]


def check_pandoc():
    pandoc_path = shutil.which("pandoc")
    if not pandoc_path:
        print("[FAIL] pandoc not found on PATH")
        return False
    try:
        subprocess.run(["pandoc", "--version"], capture_output=True, check=True, text=True)
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"[FAIL] pandoc found at {pandoc_path} but failed to run: {e}")
        return False
    print(f"[PASS] pandoc found at {pandoc_path}")
    return True


def check_module(module_name):
    try:
        importlib.import_module(module_name)
    except ImportError as e:
        print(f"[FAIL] Python package for '{module_name}' not importable: {e}")
        return False
    print(f"[PASS] Python package '{module_name}' importable")
    return True


def main():
    print(f"[INFO] Python interpreter: {sys.executable} ({sys.version.split()[0]})")

    results = [check_pandoc()]
    results += [check_module(m) for m in REQUIRED_MODULES]

    if all(results):
        print("[PASS] All dependencies satisfied")
        return 0

    print("[FAIL] One or more dependencies missing - run install.ps1 from the repo root")
    return 1


if __name__ == "__main__":
    sys.exit(main())
