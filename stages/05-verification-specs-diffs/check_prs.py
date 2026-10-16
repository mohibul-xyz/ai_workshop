#!/usr/bin/env python3
"""make lab-diffs — checkpoint for topic 9 (reading diffs critically).

1. Every seeded PR diff still applies cleanly to its base commit (git apply --check).
2. scripts/review_diff.py finds every scanner rule listed in prs/expected.json.
3. Negative control: a clean, real feature commit produces no HIGH findings
   (a scanner that cries wolf trains people to ignore it).
4. If a findings write-up exists (findings-PR-10x.md), it mentions every seeded defect id.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCANNER = ROOT / "scripts" / "review_diff.py"


def git(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def commit_for(subject: str) -> str:
    sha = git("log", "--format=%H", "-1", "--fixed-strings", f"--grep={subject}").stdout.strip()
    if not sha:
        sys.exit(f"cannot find commit with subject: {subject!r}")
    return sha


def scan(diff_text: str, scope: str = "") -> list[dict[str, object]]:
    args = [sys.executable, str(SCANNER), "-", "--json"] + (["--scope", scope] if scope else [])
    res = subprocess.run(args, input=diff_text, capture_output=True, text=True, check=False)
    findings: list[dict[str, object]] = json.loads(res.stdout)
    return findings


def main() -> int:
    exp = json.loads((HERE / "prs" / "expected.json").read_text())
    base = commit_for(exp["base_commit_subject"])
    ok = True

    with tempfile.TemporaryDirectory(prefix="prs-base-") as tmp:
        wt = Path(tmp) / "wt"
        git("worktree", "add", "--detach", "-q", str(wt), base)
        try:
            for name, spec in exp["prs"].items():
                diff = (HERE / "prs" / name).read_text()
                applies = git("apply", "--check", str(HERE / "prs" / name), cwd=wt)
                rules = {str(f["rule"]) for f in scan(diff, exp["scope"])}
                missing = [r for r in spec["scanner_rules"] if r not in rules]
                status = "OK  " if applies.returncode == 0 and not missing else "FAIL"
                ok &= status == "OK  "
                print(
                    f"{status} {name}: applies={'yes' if applies.returncode == 0 else 'NO'}  "
                    f"scanner {len(spec['scanner_rules']) - len(missing)}/"
                    f"{len(spec['scanner_rules'])} seeded rules found  "
                    f"(+{len(spec['human_only'])} human-only defects to find by reading)"
                )
                if applies.returncode:
                    print(f"  - git apply: {applies.stderr.strip()}")
                for r in missing:
                    print(f"  - scanner missed: {r}")
        finally:
            git("worktree", "remove", "--force", str(wt))

    neg = commit_for(exp["negative_control_subject"])
    highs = [f for f in scan(git("show", "--format=", neg).stdout) if f["severity"] == "HIGH"]
    print(
        f"{'OK  ' if not highs else 'FAIL'} negative control ({neg[:7]}, a clean feature commit): "
        f"{len(highs)} HIGH findings"
    )
    for f in highs:
        print(f"  - false positive: {f['rule']} {f['file']}:{f['line']}")
    ok &= not highs

    for name in exp["prs"]:
        sheet = HERE / f"findings-{name.removesuffix('.diff')}.md"
        if sheet.exists():
            text = sheet.read_text().lower()
            gaps = [
                r
                for r in exp["prs"][name]["scanner_rules"]
                if r.replace("-", " ") not in text.replace("-", " ")
            ]
            print(
                f"{'OK  ' if not gaps else 'TODO'} {sheet.name}: "
                + ("all seeded rules written up" if not gaps else f"not yet covered: {gaps}")
            )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
