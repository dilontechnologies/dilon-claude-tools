"""
Test suite for the dilon-document-form-compiler skill.

Direct-invocation style, matching tests/run_tests.py: a global
passed/failed counter via check(), explicit test calls from main(), no
pytest.
"""

import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.shared import Inches

REPO_ROOT = Path(__file__).parent.parent
FORM_COMPILER_DIR = REPO_ROOT / "skills" / "dilon-document-form-compiler"
SCRIPTS_DIR = FORM_COMPILER_DIR / "scripts"
# Shared with dilon-document-compiler - both skills use the same
# header/footer/styles-only base template, no form-specific copy.
BASE_TEMPLATE = REPO_ROOT / "templates" / "TEMPLATE_Word_Base.docx"
CHECK_DEPS_SCRIPT = SCRIPTS_DIR / "check_deps.py"
FORM_COMPILER_SCRIPT = SCRIPTS_DIR / "generate_dilon_form.py"
TEST_OUTPUT_DIR = Path(__file__).parent / "form-test-output"

SHEBANG_GUARDED_SCRIPTS = [
    CHECK_DEPS_SCRIPT,
    FORM_COMPILER_SCRIPT,
    SCRIPTS_DIR / "form_fields.py",
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
    check(result.returncode == 0, "check_deps.py exits 0 when dependencies are installed")
    check("pandoc" in result.stdout.lower(), "check_deps.py reports on pandoc")
    check("jinja2" in result.stdout.lower(), "check_deps.py reports on the jinja2 module")


def main():
    if TEST_OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(TEST_OUTPUT_DIR)
    TEST_OUTPUT_DIR.mkdir(parents=True)

    test_check_deps_runs_and_reports()

    print(f"\n{passed} passed, {failed} failed (dilon-document-form-compiler)")
    if failed == 0:
        print("\nAll form-compiler tests passed!")
        return 0
    print("\nSome form-compiler tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
