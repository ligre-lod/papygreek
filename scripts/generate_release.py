#!/usr/bin/env python3
"""Prepare or check a release.

    python scripts/generate_release.py prepare 0.1.0   # set version and date, rebuild the corpus
    python scripts/generate_release.py check 0.1.0     # check that everything says 0.1.0, print the release notes
"""
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
CITATION = ROOT / "CITATION.cff"
PYPROJECT = ROOT / "pyproject.toml"
SETTINGS = ROOT / "papygreek_to_ligre" / "settings.py"
CORPUS_DESCRIPTION = ROOT / "ttl" / "PapyGreek_corpus.ttl"
REPOSITORY = "https://github.com/ligre-lod/papygreek"


def fail(message):
    sys.exit(f"error: {message}")


def citation_field(name):
    match = re.search(rf"^{name}:\s*(\S+)\s*$", CITATION.read_text(), re.M)
    return match and match.group(1)


def changelog_section(version):
    match = re.search(rf"^## \[{re.escape(version)}\] - (\S+)\n(.*?)(?=^## |^\[)", CHANGELOG.read_text(), re.M | re.S)
    return match and (match.group(1), match.group(2).strip())


def prepare(version):
    date = datetime.date.today().isoformat()
    changelog = CHANGELOG.read_text()
    if "## [Unreleased]" not in changelog:
        fail("CHANGELOG.md has no '## [Unreleased]' section")
    if f"## [{version}]" in changelog:
        fail(f"CHANGELOG.md already has a section for {version}")
    link = re.search(r"^\[Unreleased\]: (\S+)$", changelog, re.M)
    if not link:
        fail("CHANGELOG.md has no '[Unreleased]: ...' link")
    previous = re.search(r"/compare/(v\S+)\.\.\.HEAD$", link.group(1))
    version_link = f"{REPOSITORY}/compare/{previous.group(1)}...v{version}" if previous \
        else f"{REPOSITORY}/releases/tag/v{version}"
    changelog = changelog.replace("## [Unreleased]", f"## [Unreleased]\n\n## [{version}] - {date}", 1)
    changelog = changelog.replace(link.group(0), f"[Unreleased]: {REPOSITORY}/compare/v{version}...HEAD\n"
                                                 f"[{version}]: {version_link}")
    CHANGELOG.write_text(changelog)

    citation = CITATION.read_text()
    citation = re.sub(r"^version: .*$", f"version: {version}", citation, flags=re.M)
    citation = re.sub(r"^date-released: .*$", f"date-released: {date}", citation, flags=re.M)
    CITATION.write_text(citation)
    PYPROJECT.write_text(re.sub(r'^version = ".*"$', f'version = "{version}"', PYPROJECT.read_text(), count=1, flags=re.M))
    print(f"set version {version} and date {date} in CHANGELOG.md, CITATION.cff and pyproject.toml")

    subprocess.run([sys.executable, "-m", "papygreek_to_ligre", "--refresh"], cwd=ROOT, check=True)


def check(version):
    errors = []
    if citation_field("version") != version:
        errors.append(f"CITATION.cff has version {citation_field('version')}")
    if f'\nversion = "{version}"\n' not in PYPROJECT.read_text():
        errors.append(f"pyproject.toml does not have version {version}")
    section = changelog_section(version)
    if not section:
        errors.append(f"CHANGELOG.md has no '## [{version}] - <date>' section")
    elif section[0] != citation_field("date-released"):
        errors.append(f"CHANGELOG.md date {section[0]} differs from CITATION.cff date {citation_field('date-released')}")
    if f'dcat:version "{version}"' not in CORPUS_DESCRIPTION.read_text():
        errors.append(f"{CORPUS_DESCRIPTION.relative_to(ROOT)} does not describe version {version}; run 'prepare'")
    ligre = re.search(r'^LIGRE_LEMMA_BANK_VERSION = "v(\S+)"$', SETTINGS.read_text(), re.M)
    cited = re.search(r'title: "LiGre Lemma Bank[^\n]*\n\s+version: (\S+)', CITATION.read_text())
    if not ligre or not cited or ligre.group(1) != cited.group(1):
        errors.append("the LiGre version in settings.py (LIGRE_LEMMA_BANK_VERSION) differs from the one in CITATION.cff")
    if errors:
        fail("release metadata does not match v" + version + ":\n  " + "\n  ".join(errors))
    print(section[1])


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("prepare", "check"):
        fail(__doc__.strip())
    command, version = sys.argv[1], sys.argv[2].removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail(f"'{version}' is not MAJOR.MINOR.PATCH")
    {"prepare": prepare, "check": check}[command](version)
