from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from analysis.docker import Finding, inspect_files

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "fixtures"

ANALYZERS = (inspect_files,)


def _fixture_dirs() -> list[Path]:
    return sorted(d for d in FIXTURES_ROOT.iterdir() if d.is_dir() and (d / "expected-findings.yaml").is_file())


def _load_expected(fixture_dir: Path) -> list[dict[str, Any]]:
    raw = yaml.safe_load((fixture_dir / "expected-findings.yaml").read_text(encoding="utf-8"))
    return list(raw.get("findings") or [])


def _analyze(fixture_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    for analyzer in ANALYZERS:
        findings.extend(analyzer(str(fixture_dir)))
    return findings


def _key(rule_id: str, file: str, line: int | None) -> tuple[str, str, int | None]:
    return (rule_id, file, line)


def test_fixture_directories_are_discovered() -> None:
    assert _fixture_dirs(), f"no fixture directories found under {FIXTURES_ROOT}"


@pytest.mark.parametrize("fixture_dir", _fixture_dirs(), ids=lambda d: d.name)
def test_detector_matches_golden_dataset(fixture_dir: Path) -> None:
    expected = {_key(f["rule_id"], f["file"], f.get("line")) for f in _load_expected(fixture_dir)}
    actual = {_key(f.rule_id, f.file, f.line) for f in _analyze(fixture_dir)}

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    assert not missing, f"{fixture_dir.name}: detector missed {missing}"
    assert not unexpected, f"{fixture_dir.name}: detector emitted false positives {unexpected}"


@pytest.mark.parametrize("fixture_dir", _fixture_dirs(), ids=lambda d: d.name)
def test_findings_carry_user_facing_text(fixture_dir: Path) -> None:
    for finding in _analyze(fixture_dir):
        assert finding.message.strip(), f"{fixture_dir.name}: {finding.rule_id} has an empty message"
        assert finding.remediation.strip(), f"{fixture_dir.name}: {finding.rule_id} has an empty remediation"
