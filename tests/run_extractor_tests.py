"""
Test suite for the dilon-document-extractor skill.

Direct-invocation style, matching tests/run_tests.py: a global
passed/failed counter via check(), explicit test calls from main(), no
pytest.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
EXTRACTOR_DIR = REPO_ROOT / "skills" / "dilon-document-extractor"
SCRIPTS_DIR = EXTRACTOR_DIR / "scripts"
CHECK_DEPS_SCRIPT = SCRIPTS_DIR / "check_deps.py"
EXTRACT_DOCX_SCRIPT = SCRIPTS_DIR / "extract_docx.py"
EXTRACT_PDF_SCRIPT = SCRIPTS_DIR / "extract_pdf.py"
TEST_OUTPUT_DIR = Path(__file__).parent / "extractor-test-output"

SHEBANG_GUARDED_SCRIPTS = [
    CHECK_DEPS_SCRIPT,
    EXTRACT_DOCX_SCRIPT,
    EXTRACT_PDF_SCRIPT,
    Path(__file__),
]

sys.path.insert(0, str(SCRIPTS_DIR))

passed = 0
failed = 0


def check(condition, message):
    global passed, failed
    if condition:
        print(f"[PASS] {message}")
        passed += 1
    else:
        print(f"[FAIL] {message}")
        failed += 1


def test_check_deps_runs_and_reports():
    result = subprocess.run(
        [sys.executable, str(CHECK_DEPS_SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "check_deps.py exits 0 when python-docx/pyyaml/pymupdf are installed")
    check("docx" in result.stdout, "check_deps.py reports on the docx module")
    check("yaml" in result.stdout, "check_deps.py reports on the yaml module")
    check("fitz" in result.stdout, "check_deps.py reports on the fitz (pymupdf) module")


def main():
    if TEST_OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(TEST_OUTPUT_DIR)
    TEST_OUTPUT_DIR.mkdir(parents=True)

    test_check_deps_runs_and_reports()

    print(f"\n{passed} passed, {failed} failed (dilon-document-extractor)")
    if failed == 0:
        print("\nAll extractor tests passed!")
        return 0
    print("\nSome extractor tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
