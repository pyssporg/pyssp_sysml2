"""Static policy for the fixture tree: every case explains and lists its bytes.

A fixture directory is only evidence if a reader can tell what it is, what
proves it, and which files belong to it. Those facts live in ``case.md`` next to
the data; this file makes the record mandatory instead of customary. It also
keeps documents out of test modules: a SysML architecture belongs in a file, not
in a 40-line literal. It reads text and stat only, so it is ``static``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
GOLDEN = TESTS / "golden"
FIXTURES = TESTS / "fixtures"

#: Files a case record must name, by suffix.
DATA_SUFFIXES = frozenset({".sysml", ".ssd", ".ssv", ".ssm", ".xml", ".json", ".csv", ".txt"})

#: A literal with more newlines than this is a document, and documents live in
#: ``tests/fixtures/``. Fragments that a test interpolates stay inline.
INLINE_NEWLINE_LIMIT = 15

#: Exceptions, keyed ``<file>:<line>`` with the reason it stays inline.
INLINE_ALLOWLIST: dict[str, str] = {}

#: The case record is the manifest, not a generated artifact.
RECORD = "case.md"

#: Inputs, not outputs: a golden is what the generator produces.
INPUT_SUFFIX = ".sysml"

#: Section headings every case record must carry; see the template in
#: ``project-test-suites/templates/conversion-case.md`` and ``tests/README.md``.
REQUIRED_HEADINGS = (
    "# Case:",
    "## Artifacts",
    "## What this case proves",
    "## Update history",
)

#: Field labels, one per line, in the record's bullet block.
REQUIRED_FIELDS = (
    "Conversion",
    "Requirement / fault",
    "Level",
    "Input",
    "Expected",
    "Independent oracle",
    "Comparison",
    "Normalization",
    "Volatile fields",
    "Update policy",
    "Notes",
)

#: Directories that are cases: every directory directly under ``tests/golden``.
CASES = tuple(sorted(path.name for path in GOLDEN.iterdir() if path.is_dir()))

#: A backticked token in ``case.md`` is how a path is declared.
_BACKTICKED = re.compile(r"`([^`\n]+)`")


def _record(case: str) -> Path:
    return GOLDEN / case / RECORD


def _declared(case: str) -> set[str]:
    """Relative paths the case record names anywhere in its text."""
    text = _record(case).read_text(encoding="utf-8")
    return {
        token.strip().removeprefix("./")
        for token in _BACKTICKED.findall(text)
    }


def _artifacts(case: str) -> set[str]:
    """Generated files in the case directory, as relative posix paths."""
    case_dir = GOLDEN / case
    return {
        path.relative_to(case_dir).as_posix()
        for path in sorted(case_dir.rglob("*"))
        if path.is_file()
        and path.name != RECORD
        and path.suffix != INPUT_SUFFIX
        and "__pycache__" not in path.parts
    }


@pytest.mark.parametrize("case", CASES)
def test_every_golden_case_has_a_case_record(case: str) -> None:
    """A case without provenance is a directory of blessed bytes."""
    assert CASES, "no golden cases found"
    assert _record(case).is_file(), (
        f"{_record(case).relative_to(GOLDEN.parent.parent)} is missing; "
        "every case directory needs a case.md"
    )


@pytest.mark.parametrize("case", CASES)
def test_the_case_record_carries_the_required_contract(case: str) -> None:
    text = _record(case).read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    missing += [
        f"- **{field}:**" for field in REQUIRED_FIELDS
        if f"- **{field}:**" not in text
    ]
    assert not missing, (
        f"{case}/{RECORD} is missing required headings or fields:\n"
        + "\n".join(missing)
    )


@pytest.mark.parametrize("case", CASES)
def test_the_case_record_lists_every_artifact(case: str) -> None:
    """An unlisted file is an artifact nobody reviewed or claimed."""
    unlisted = sorted(_artifacts(case) - _declared(case))
    assert not unlisted, (
        f"{case}/{RECORD} does not list these artifacts by relative path:\n"
        + "\n".join(unlisted)
    )


def test_every_golden_case_is_exercised_by_the_golden_test() -> None:
    """A case the converter test does not name is never compared or validated."""
    from tests.test_golden_artifacts import CASES as EXERCISED

    unexercised = sorted(set(CASES) - set(EXERCISED))
    assert not unexercised, (
        "golden case directories not in CASES in tests/test_golden_artifacts.py: "
        f"{unexercised}"
    )


# ---------------------------------------------------------------------------
# Fixture tree: input documents and case records
# ---------------------------------------------------------------------------

def _fixture_directories() -> list[Path]:
    """One case directory per subject: the direct children of ``fixtures/``."""
    return sorted(path for path in FIXTURES.iterdir() if path.is_dir())


def _fixture_files(case_dir: Path) -> set[str]:
    return {
        path.relative_to(case_dir).as_posix()
        for path in sorted(case_dir.rglob("*"))
        if path.is_file() and path.suffix in DATA_SUFFIXES
    }


def test_every_fixture_directory_has_a_case_record() -> None:
    missing = [
        directory.name
        for directory in _fixture_directories()
        if not (directory / "case.md").is_file()
    ]

    assert not missing, f"fixture directories without case.md: {missing}"


def test_every_fixture_file_is_listed_in_its_case_record() -> None:
    unlisted: dict[str, list[str]] = {}
    for directory in _fixture_directories():
        declared = _declared_in(directory / "case.md")
        missing = sorted(_fixture_files(directory) - declared)
        if missing:
            unlisted[directory.name] = missing

    assert not unlisted, (
        "fixture files not named in their case.md:\n"
        + "\n".join(f"  {case}: {files}" for case, files in unlisted.items())
    )


def _declared_in(record: Path) -> set[str]:
    return {
        token.strip().removeprefix("./")
        for token in _BACKTICKED.findall(record.read_text(encoding="utf-8"))
    }


def test_test_modules_do_not_embed_large_documents() -> None:
    """A document over the limit is a fixture that was never committed."""
    offenders: list[str] = []
    for path in sorted(TESTS.glob("*.py")):
        if path.name in {"test_fixture_policy.py", "fixture_files.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in docstrings:
                continue
            if node.value.count("\n") < INLINE_NEWLINE_LIMIT:
                continue
            key = f"{path.name}:{node.lineno}"
            if key in INLINE_ALLOWLIST:
                continue
            offenders.append(key)

    assert not offenders, (
        f"inline documents of {INLINE_NEWLINE_LIMIT}+ lines; move them to "
        "tests/fixtures/<subject>/ and load with fixture_text():\n"
        + "\n".join(f"  {key}" for key in offenders)
    )


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Ids of docstring constants, which are prose, not embedded documents."""
    found: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def test_fixture_paths_resolve_from_the_module() -> None:
    """A fixture read through the cwd breaks under a different rootdir."""
    offenders = [
        f"{path.name}:{index}"
        for path in sorted(TESTS.glob("*.py"))
        if path.name not in {"test_fixture_policy.py", "fixture_files.py"}
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if 'Path("tests/' in line or "Path('tests/" in line
    ]

    assert not offenders, f"cwd-relative fixture paths: {offenders}"
