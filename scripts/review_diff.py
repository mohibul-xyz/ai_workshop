#!/usr/bin/env python3
"""Risk scanner for diffs (topic 9: reading diffs critically). Stdlib only.

It finds suspicious LINES. It cannot judge INTENT — a human (or the reviewer subagent)
must read every finding and decide. Use with stages/05-verification-specs-diffs/review-checklist.md.

Usage:
  python3 scripts/review_diff.py PR-101.diff [--scope app/,tests/] [--json]
  python3 scripts/review_diff.py --git main...HEAD
  git diff | python3 scripts/review_diff.py -

Exit code: 1 if any HIGH finding, else 0.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

HIGH, MED, LOW = "HIGH", "MED", "LOW"
SIZE_LIMIT = 400


@dataclass
class FileDiff:
    path: str
    old_path: str
    new_file: bool = False
    deleted: bool = False
    added: list[tuple[int, str]] = field(default_factory=list)  # (new line no, text)
    removed: list[tuple[int, str]] = field(default_factory=list)  # (old line no, text)
    newside: dict[int, str] = field(default_factory=dict)  # added + context lines, new numbering

    def enclosing_def(self, line: int) -> str:
        """Name of the top-level function containing `line` on the new side ('' if unknown)."""
        for n in range(line, 0, -1):
            m = re.match(r"def (\w+)\(", self.newside.get(n, ""))
            if m:
                return m.group(1)
        return ""


@dataclass
class Finding:
    severity: str
    rule: str
    file: str
    line: int
    message: str
    evidence: str


def parse(diff: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    cur: FileDiff | None = None
    old_no = new_no = 0
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            m = re.match(r"diff --git a/(\S+) b/(\S+)", raw)
            if m:
                cur = FileDiff(path=m.group(2), old_path=m.group(1))
                files.append(cur)
            continue
        if cur is None:
            continue
        if raw.startswith("new file mode"):
            cur.new_file = True
        elif raw.startswith("deleted file mode"):
            cur.deleted = True
        elif raw.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            if m:
                old_no, new_no = int(m.group(1)), int(m.group(2))
        elif raw.startswith(("+++", "---")):
            continue
        elif raw.startswith("+"):
            cur.added.append((new_no, raw[1:]))
            cur.newside[new_no] = raw[1:]
            new_no += 1
        elif raw.startswith("-"):
            cur.removed.append((old_no, raw[1:]))
            old_no += 1
        elif raw.startswith(" "):
            cur.newside[new_no] = raw[1:]
            old_no += 1
            new_no += 1
    return files


def _norm(line: str) -> str:
    return re.sub(r"[\s'\",()]|#\s*noqa\S*", "", line)


LOOSENERS = ("sorted(", " in ", ">=", "<=", "len(", "any(", "is not None")


def _tokens(line: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+|\"[^\"]*\"|'[^']*'", line))


def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _weakens(old: str, new: str) -> bool:
    return any(w in new and w not in old for w in LOOSENERS)


SQL_WORDS = re.compile(
    r"\b(SELECT\s|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|WHERE\s|I?LIKE\s|ORDER\s+BY)", re.I
)
FSTRING = re.compile(r"""\bf(['"])(.*?)\1""")
SECRET_RE = re.compile(
    r"(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{20,}|"
    r"(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{6,}['\"])",
    re.I,
)


def scan(files: list[FileDiff], scope: list[str]) -> list[Finding]:
    out: list[Finding] = []

    seen: set[tuple[str, str, int]] = set()

    def add(sev: str, rule: str, f: FileDiff, line: int, msg: str, ev: str = "") -> None:
        if (rule, f.path, line) not in seen:
            seen.add((rule, f.path, line))
            out.append(Finding(sev, rule, f.path, line, msg, ev.strip()[:160]))

    total = 0
    for f in files:
        total += len(f.added) + len(f.removed)
        is_test = f.path.startswith("tests/") or "/test_" in f.path or f.path.startswith("test_")
        is_migration = f.path.startswith("migrations/versions/")

        # --- scope
        if scope and not any(f.path.startswith(s) for s in scope):
            add(MED, "out-of-scope", f, 0, f"file outside declared scope {scope}")

        # --- formatting-only churn (same tokens, different layout)
        if f.added and f.removed and not f.new_file and not is_migration:
            if Counter(_norm(t) for _, t in f.added if _norm(t)) == Counter(
                _norm(t) for _, t in f.removed if _norm(t)
            ) or sorted("".join(_norm(t) for _, t in f.added)) == sorted(
                "".join(_norm(t) for _, t in f.removed)
            ):
                add(
                    MED,
                    "formatting-only",
                    f,
                    f.added[0][0],
                    "only formatting/noqa changes — unrelated churn hides real changes",
                )

        # --- tests
        if is_test:
            if f.deleted:
                add(HIGH, "test-file-deleted", f, 0, "a whole test file was deleted")
            removed_asserts = [(n, t) for n, t in f.removed if re.match(r"\s*assert\b", t)]
            added_asserts = [t for _, t in f.added if re.match(r"\s*assert\b", t)]
            for n, t in f.removed:
                if re.match(r"\s*def test_", t) and not any(
                    _norm(t) == _norm(a) for _, a in f.added
                ):
                    add(HIGH, "test-deleted", f, n, "test function removed", t)
            for n, t in removed_asserts:
                if _norm(t) in {_norm(a) for a in added_asserts}:
                    continue
                best = max(added_asserts, key=lambda a: _similar(t, a), default="")
                if best and _similar(t, best) >= 0.6 and _weakens(t, best):
                    add(
                        HIGH,
                        "assertion-weakened",
                        f,
                        n,
                        "assertion loosened (sorted/in/>=/len) — it may no longer catch the "
                        "bug it was written for",
                        f"{t.strip()}  →  {best.strip()}",
                    )
                elif best and _similar(t, best) >= 0.8 and _tokens(t) <= _tokens(best):
                    add(
                        MED,
                        "assertion-rewritten",
                        f,
                        n,
                        "assertion reshaped but keeps every original check — confirm only the "
                        "response shape changed",
                        f"{t.strip()}  →  {best.strip()}",
                    )
                else:
                    add(
                        HIGH,
                        "assertion-removed",
                        f,
                        n,
                        "assertion removed — does the test still prove the behaviour?",
                        t,
                    )
            for n, t in f.added:
                if re.search(r"pytest\.mark\.(skip|xfail)|pytest\.skip\(|@unittest\.skip", t):
                    add(HIGH, "skip-xfail", f, n, "test skipped / expected to fail", t)

        # --- migrations
        if is_migration and not f.new_file:
            add(
                HIGH,
                "migration-edited",
                f,
                (f.added or f.removed or [(0, "")])[0][0],
                "committed migration modified — databases that ran it will drift; "
                "write a new revision",
            )
        if is_migration:
            text = "\n".join(t for _, t in f.added)
            for n, t in f.added:
                if re.search(r"op\.drop_(column|table)\(", t) and f.enclosing_def(n) != "downgrade":
                    add(
                        HIGH,
                        "destructive-migration",
                        f,
                        n,
                        "drop_column/drop_table loses data — needs explicit human approval",
                        t,
                    )
            m = re.search(r"def downgrade\(\)[^:]*:\s*\n((?:\s*#.*\n)*)\s*pass\b", text + "\n")
            if m:
                line = next((n for n, t in f.added if "def downgrade" in t), 0)
                add(HIGH, "empty-downgrade", f, line, "downgrade() does nothing — irreversible")

        # --- per added line
        for n, t in f.added:
            if any(SQL_WORDS.search(m.group(2)) for m in FSTRING.finditer(t)):
                add(
                    HIGH,
                    "sql-fstring",
                    f,
                    n,
                    "SQL built with an f-string — injection risk; use bound parameters",
                    t,
                )
            elif re.search(r"['\"]\s*%\s*[\w(]", t) and SQL_WORDS.search(t):
                add(HIGH, "sql-fstring", f, n, "SQL built with % formatting — injection risk", t)
            if re.match(r"\s*except\s*:", t) or re.match(
                r"\s*except\s+(BaseException|Exception)\b", t
            ):
                add(MED, "broad-except", f, n, "broad except can swallow real errors", t)
            if SECRET_RE.search(t):
                add(HIGH, "secret", f, n, "looks like a hard-coded secret", t)
            if re.search(r"#\s*(TODO|FIXME|XXX|HACK)\b", t):
                add(LOW, "todo", f, n, "unfinished work marker", t)
            if re.search(r"\.order_by\(.*\.desc\(\)|\.limit\(|\.offset\(", t) and not is_test:
                add(
                    MED,
                    "behaviour-change",
                    f,
                    n,
                    "ordering/limit changed — default ordering is part of the API contract",
                    t,
                )
            if re.match(r"\s*[A-Z_]{3,}\s*=\s*\d+", t) and not is_test:
                add(
                    LOW,
                    "magic-constant",
                    f,
                    n,
                    "new numeric constant — check the value and comment agree (off-by-one?)",
                    t,
                )

    if total > SIZE_LIMIT:
        out.append(
            Finding(
                MED,
                "size",
                "*",
                0,
                f"{total} changed lines > {SIZE_LIMIT}: too big to review well — split it",
                "",
            )
        )
    return out


def load(args: argparse.Namespace) -> str:
    if args.git:
        res = subprocess.run(["git", "diff", args.git], capture_output=True, text=True, check=False)
        if res.returncode != 0:
            sys.exit(res.stderr)
        return res.stdout
    if args.diff in (None, "-"):
        return sys.stdin.read()
    return Path(args.diff).read_text(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("diff", nargs="?", help="diff file, or - for stdin")
    ap.add_argument("--git", help="git diff range, e.g. main...HEAD")
    ap.add_argument("--scope", default="", help="comma-separated path prefixes in scope")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    files = parse(load(args))
    findings = scan(files, [s for s in args.scope.split(",") if s])
    order = {HIGH: 0, MED: 1, LOW: 2}
    findings.sort(key=lambda x: (order[x.severity], x.file, x.line))

    if args.json:
        print(json.dumps([asdict(x) for x in findings], indent=2))
    else:
        changed = sum(len(f.added) + len(f.removed) for f in files)
        print(f"review_diff: {len(files)} files, {changed} changed lines, {len(findings)} findings")
        for x in findings:
            loc = f"{x.file}:{x.line}" if x.line else x.file
            print(f"  [{x.severity:4}] {x.rule:22} {loc}\n         {x.message}")
            if x.evidence:
                print(f"         > {x.evidence}")
        print(
            "\nThe scanner flags lines; you judge intent. Walk review-checklist.md before deciding."
        )
    return 1 if any(x.severity == HIGH for x in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
