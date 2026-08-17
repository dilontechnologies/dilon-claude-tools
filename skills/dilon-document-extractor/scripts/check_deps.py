"""Preflight dependency check for the dilon-document-extractor skill."""

import importlib
import sys

REQUIRED_MODULES = ["docx", "yaml", "fitz"]


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

    results = [check_module(m) for m in REQUIRED_MODULES]

    if all(results):
        print("[PASS] All dependencies satisfied")
        return 0

    print("[FAIL] One or more dependencies missing - run install.ps1 from the repo root")
    return 1


if __name__ == "__main__":
    sys.exit(main())
