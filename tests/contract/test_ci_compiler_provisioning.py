from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
WARMUP_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "compiler_warmup.tex"

TECTONIC_VERSION = "0.16.9"
TECTONIC_ARCHIVE_SHA256 = (
    "f3c825128095dc3399ea11c08c18035b33050a216930c295c79e8eb11bd21de4"
)


def test_ci_installs_the_pinned_verified_tectonic_release() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert f"tectonic-{TECTONIC_VERSION}-x86_64-unknown-linux-gnu.tar.gz" in workflow
    assert TECTONIC_ARCHIVE_SHA256 in workflow
    assert "sha256sum --check --strict" in workflow


def test_ci_warms_the_locked_template_dependencies() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    fixture = WARMUP_FIXTURE.read_text(encoding="utf-8")

    assert "XDG_CACHE_HOME: ${{ github.workspace }}/.tools/tectonic-cache" in workflow
    assert ".tools/tectonic --untrusted --keep-logs" in workflow
    assert "tests/fixtures/compiler_warmup.tex" in workflow
    assert "\\usepackage[T1]{fontenc}" in fixture
    assert "\\usepackage[hidelinks]{hyperref}" in fixture
