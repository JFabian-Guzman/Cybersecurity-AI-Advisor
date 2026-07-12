from __future__ import annotations

import os
import os.path
import re
from collections.abc import Iterator
from dataclasses import dataclass

_SECRET_KEY_PATTERN = re.compile(r"(KEY|SECRET|PASSWORD|PASSWD|TOKEN|CREDENTIAL)", re.IGNORECASE)
_REMOTE_URL_PATTERN = re.compile(r"^(https?|ftp)://", re.IGNORECASE)
_VAR_REF_PATTERN = re.compile(r"^\$")
_INSTRUCTION_PATTERN = re.compile(r"^([A-Za-z]+)\s*(.*)$")
_FROM_PATTERN = re.compile(r"^(\S+)(?:\s+AS\s+(\S+))?", re.IGNORECASE)

# Package manager pinning syntax
_PIN_OPERATOR = {
    "apt-get": "=",
    "apt": "=",
    "pip": "==",
    "pip3": "==",
    "npm": "@",
    "yarn": "@",
    "apk": "=",
    "yum": "-",
    "dnf": "-",
}


@dataclass
class Finding:
    rule_id: str
    severity: str
    file: str
    line: int | None
    message: str


def _is_dockerfile(name: str) -> bool:
    return name == "Dockerfile" or name.lower().endswith(".dockerfile")


def _iter_instructions(lines: list[str]) -> Iterator[tuple[int, str, str]]:
    buffer: list[str] = []
    start_line: int | None = None

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.rstrip("\r\n").strip()

        if not buffer:
            if not stripped or stripped.startswith("#"):
                continue
            start_line = idx

        ## If the instruction has more than one line iterates over the instruction
        if stripped.endswith("\\"):
            buffer.append(stripped[:-1].strip())
            continue

        buffer.append(stripped)
        full = " ".join(buffer).strip()
        buffer = []

        # Extracts the keyword (RUN, FROM, ENV, etc.)
        match = _INSTRUCTION_PATTERN.match(full)
        if not match or start_line is None:
            continue

        # start_line - Line number
        # match.group(1).upper() - Keyword
        # match.group(2).strip() — the rest of the line
        yield start_line, match.group(1).upper(), match.group(2).strip()
        start_line = None


def _analyze_dockerfile(path: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_user(path, lines))
    findings.extend(_check_tags(path, lines))
    findings.extend(_check_secrets(path, lines))
    findings.extend(_check_remote_url(path, lines))
    findings.extend(_check_version_pinning(path, lines))
    return findings


def _check_user(path: str, lines: list[str]) -> list[Finding]:
    for _line_no, keyword, _content in _iter_instructions(lines):
        if keyword == "USER":
            return []

    return [
        Finding(
            rule_id="DF001",
            severity="HIGH",
            file=path,
            line=None,
            message=(
                "No USER directive found — the container runs as root by default. Add a "
                "USER directive with a non-root user before CMD/ENTRYPOINT."
            ),
        )
    ]


def _check_tags(path: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    stage_names: set[str] = set()

    for line_no, keyword, content in _iter_instructions(lines):
        if keyword != "FROM":
            continue

        match = _FROM_PATTERN.match(content)
        if not match:
            continue

        image_ref, stage_alias = match.group(1), match.group(2)

        # Builds up a memory of all known internal stage names
        if image_ref in stage_names:
            if stage_alias:
                stage_names.add(stage_alias)
            continue

        if stage_alias:
            stage_names.add(stage_alias)

        if "@" in image_ref:
            continue  # pinned by digest

        last_segment = image_ref.rsplit("/", 1)[-1]
        # Check if has a tag
        if ":" in last_segment:
            tag = last_segment.rsplit(":", 1)[-1]
            if tag != "latest":
                continue
            message = (
                f'Base image "{image_ref}" uses a mutable tag. Pin to an explicit version '
                "(and ideally a digest) for reproducible, auditable builds."
            )
        else:
            message = (
                f'Base image "{image_ref}" has no tag (defaults to :latest). Pin to an '
                "explicit version (and ideally a digest) for reproducible, auditable builds."
            )

        findings.append(Finding(rule_id="DF002", severity="MEDIUM", file=path, line=line_no, message=message))

    return findings


# Delete comments
def _strip_inline_comment(content: str) -> str:
    idx = content.find(" #")
    return content[:idx].strip() if idx != -1 else content.strip()


# Extract keys
def _parse_key_values(content: str) -> list[tuple[str, str]]:
    # Search secrets - Modern syntax
    if "=" in content:
        return re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=(\"[^\"]*\"|'[^']*'|\S*)", content)
    # Search secrets - Old syntax
    parts = content.split(None, 1)
    if len(parts) == 2:
        return [(parts[0], parts[1].strip())]
    if len(parts) == 1:
        return [(parts[0], "")]
    return []


def _check_secrets(path: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []

    for line_no, keyword, content in _iter_instructions(lines):
        if keyword not in ("ARG", "ENV"):
            continue

        content = _strip_inline_comment(content)

        for name, value in _parse_key_values(content):
            if not value or _VAR_REF_PATTERN.match(value):
                continue
            if not _SECRET_KEY_PATTERN.search(name):
                continue

            if keyword == "ARG":
                source, remediation = (
                    "ARG default value",
                    "Pass secrets at build/run time (e.g. --secret or runtime env "
                    "injection), never as a default baked into the image.",
                )
            else:
                source, remediation = (
                    "ENV value",
                    "Use a secrets manager or runtime-injected environment variable "
                    "instead of embedding credentials in the image.",
                )

            findings.append(
                Finding(
                    rule_id="DF003",
                    severity="CRITICAL",
                    file=path,
                    line=line_no,
                    message=f"Hardcoded secret detected in {source} ({name}). {remediation}",
                )
            )

    return findings


def _check_remote_url(path: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []

    for line_no, keyword, content in _iter_instructions(lines):
        if keyword != "ADD":
            continue

        tokens = [t for t in content.split() if not t.startswith("--")]
        for src in tokens[:-1]:  # last token is always the destination
            if not _REMOTE_URL_PATTERN.match(src):
                continue

            findings.append(
                Finding(
                    rule_id="DF004",
                    severity="HIGH",
                    file=path,
                    line=line_no,
                    message=(
                        f"ADD fetches a remote URL ({src}). Remote content is unverified "
                        "at build time; use COPY with a vetted local artifact, or curl "
                        "plus checksum verification in a RUN step instead."
                    ),
                )
            )

    return findings


def _extract_packages(tokens: list[str], flag_values: set[str]) -> list[str]:
    packages: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("-"):
            # Skip flag and value
            i += 2 if tok in flag_values else 1
            continue
        packages.append(tok)
        i += 1
    return packages


def _pinning_finding(path: str, line_no: int, package: str, manager: str) -> Finding:
    operator = _PIN_OPERATOR.get(manager, "=")
    return Finding(
        rule_id="DF005",
        severity="MEDIUM",
        file=path,
        line=line_no,
        message=(
            f'Package "{package}" installed via {manager} without a version pin. Pin an '
            f"exact version (e.g. {package}{operator}<version>) so builds are reproducible "
            "and not silently upgraded to a vulnerable release."
        ),
    )


def _check_segment_pinning(tokens: list[str], path: str, line_no: int) -> list[Finding]:
    if len(tokens) < 2:
        return []

    manager, sub = tokens[0], tokens[1]
    findings: list[Finding] = []

    if manager in ("apt-get", "apt") and sub == "install":
        for pkg in _extract_packages(tokens[2:], flag_values={"-t"}):
            if "=" not in pkg:
                findings.append(_pinning_finding(path, line_no, pkg, manager))

    elif manager in ("pip", "pip3") and sub == "install":
        flag_values = {"-r", "-i", "-e", "--index-url", "--extra-index-url"}
        for pkg in _extract_packages(tokens[2:], flag_values=flag_values):
            if not re.search(r"(==|>=|<=|~=|@)", pkg):
                findings.append(_pinning_finding(path, line_no, pkg, manager))

    elif manager in ("npm", "yarn") and sub in ("install", "i", "add", "ci"):
        for pkg in _extract_packages(tokens[2:], flag_values=set()):
            name = pkg[1:] if pkg.startswith("@") else pkg  # allow scoped @scope/pkg
            if "@" not in name:
                findings.append(_pinning_finding(path, line_no, pkg, manager))

    elif manager == "apk" and sub == "add":
        for pkg in _extract_packages(tokens[2:], flag_values=set()):
            if "=" not in pkg:
                findings.append(_pinning_finding(path, line_no, pkg, manager))

    elif manager in ("yum", "dnf") and sub == "install":
        for pkg in _extract_packages(tokens[2:], flag_values=set()):
            if not re.search(r"-\d", pkg):
                findings.append(_pinning_finding(path, line_no, pkg, manager))

    return findings


def _check_version_pinning(path: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []

    for line_no, keyword, content in _iter_instructions(lines):
        if keyword != "RUN":
            continue

        for segment in re.split(r"&&|;", content):
            tokens = segment.split()
            findings.extend(_check_segment_pinning(tokens, path, line_no))

    return findings


def inspect_files(repo_path: str) -> list[Finding]:
    """Scan every Dockerfile under repo_path and return all DF001-DF005 findings."""
    if not os.path.isdir(repo_path):
        return []

    dockerfile_paths: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(repo_path):
        for f in filenames:
            if not _is_dockerfile(f):
                continue
            full_path = os.path.join(dirpath, f)
            relative_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
            dockerfile_paths.append(relative_path)

    findings: list[Finding] = []
    for relative_path in sorted(dockerfile_paths):
        full_path = os.path.join(repo_path, relative_path)
        try:
            with open(full_path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue

        findings.extend(_analyze_dockerfile(relative_path, lines))

    return findings
