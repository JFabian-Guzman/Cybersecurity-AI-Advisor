from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from analysis.docker import Finding, inspect_files

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "fixtures"

# Category = the fixture's top-level parent dir under fixtures/ (Docker, K8s, ...).
# A category with no analyzer registered yet has its fixtures skipped rather than
# failed, so new golden-dataset fixtures can land ahead of the detector that
# implements them (see fixtures/K8s — Sprint 2 / S2.1).
CATEGORY_ANALYZERS: dict[str, tuple[Callable[[str], list[Finding]], ...]] = {
    "Docker": (inspect_files,),
    # "K8s": (kubernetes.analyze,)  # once backend/analysis/kubernetes.py lands (S2.1)
}


def _fixture_dirs() -> list[Path]:
    return sorted({p.parent for p in FIXTURES_ROOT.rglob("expected-findings.yaml")})


def _category(fixture_dir: Path) -> str:
    return fixture_dir.relative_to(FIXTURES_ROOT).parts[0]


def _load_expected(fixture_dir: Path) -> list[dict[str, Any]]:
    raw = yaml.safe_load((fixture_dir / "expected-findings.yaml").read_text(encoding="utf-8"))
    return list(raw.get("findings") or [])


def _analyze(fixture_dir: Path, analyzers: tuple[Callable[[str], list[Finding]], ...]) -> list[Finding]:
    findings: list[Finding] = []
    for analyzer in analyzers:
        findings.extend(analyzer(str(fixture_dir)))
    return findings


def _key(rule_id: str, file: str, line: int | None) -> tuple[str, str, int | None]:
    return (rule_id, file, line)


def test_fixture_directories_are_discovered() -> None:
    assert _fixture_dirs(), f"no fixture directories found under {FIXTURES_ROOT}"


@pytest.mark.parametrize("fixture_dir", _fixture_dirs(), ids=lambda d: d.name)
def test_detector_matches_golden_dataset(fixture_dir: Path) -> None:
    analyzers = CATEGORY_ANALYZERS.get(_category(fixture_dir))
    if not analyzers:
        pytest.skip(f"no analyzer registered for category {_category(fixture_dir)!r} yet")

    expected = {_key(f["rule_id"], f["file"], f.get("line")) for f in _load_expected(fixture_dir)}
    actual = {_key(f.rule_id, f.file, f.line) for f in _analyze(fixture_dir, analyzers)}

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    assert not missing, f"{fixture_dir.name}: detector missed {missing}"
    assert not unexpected, f"{fixture_dir.name}: detector emitted false positives {unexpected}"


@pytest.mark.parametrize("fixture_dir", _fixture_dirs(), ids=lambda d: d.name)
def test_findings_carry_user_facing_text(fixture_dir: Path) -> None:
    analyzers = CATEGORY_ANALYZERS.get(_category(fixture_dir))
    if not analyzers:
        pytest.skip(f"no analyzer registered for category {_category(fixture_dir)!r} yet")

    for finding in _analyze(fixture_dir, analyzers):
        assert finding.message.strip(), f"{fixture_dir.name}: {finding.rule_id} has an empty message"
        assert finding.remediation.strip(), f"{fixture_dir.name}: {finding.rule_id} has an empty remediation"
