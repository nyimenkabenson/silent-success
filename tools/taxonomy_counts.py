"""Check the taxonomy's own arithmetic against its own instance table.

`docs/taxonomy.md` states a total in its opening line, declares a count and a
named row list per class, and carries a table assigning every row a class or
marking it excluded or unresolved. Those numbers must agree. Nothing checked
that they did, and on 2026-10-05 they disagreed for two hours: S7 went into the
table and into the verification-layer finding while class 3's count stayed at
four, so the per-class counts summed to 23 against a stated 27. That is
instance S8 - an evidence artefact describing a state that no longer matched.

Three outcomes, because a document has two states but a reader needs three:

  PASS            - the arithmetic holds.
  FAIL            - it does not, and the reason names every disagreement.
  CANNOT_EVALUATE - the document could not be read in the shape expected. A
                    moved heading or reworded line is a parse failure, not a
                    finding, and must never be reported as one.

The sabotage sweep does NOT cover this file: it scans `guards/`, and this
asserts over a document rather than over a security tool. Its negative controls
are the explicit tests in `tests/test_taxonomy_counts.py`.
"""
import re
from pathlib import Path

from guards.verdict import Outcome, Verdict

GUARD = "doc.taxonomy_counts"

_TENS = {"twenty": 20, "thirty": 30, "forty": 40}
_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
          "six": 6, "seven": 7, "eight": 8, "nine": 9}

TOTAL = re.compile(
    r"\b(twenty|thirty|forty)(?:-(one|two|three|four|five|six|seven|eight|nine))?"
    r"\s+instances\b")
CLASS_HEADING = re.compile(r"^### Class (\d+)\b")
INSTANCES = re.compile(r"^\*\*Instances: (\d+)(?: counted)?\*\*\s+\(rows? ([^)]+)\)")
INSTANCES_LOOSE = re.compile(r"^\*\*Instances:")
EXCLUDED_CELL = "**excluded**"
UNRESOLVED_CELL = "\u2014"


def check_taxonomy_counts(path="docs/taxonomy.md"):
    path = Path(path)
    evidence = {"document": str(path)}

    def cannot(reason):
        return Verdict(GUARD, Outcome.CANNOT_EVALUATE, reason, evidence)

    if not path.is_file():
        return cannot("taxonomy document not found")
    lines = path.read_text().splitlines()

    m = TOTAL.search("\n".join(lines[:20]))
    if not m:
        return cannot("no stated instance total in the opening lines")
    total = _TENS[m.group(1)] + (_UNITS[m.group(2)] if m.group(2) else 0)
    evidence["stated_total"] = total

    current, declared = None, {}
    for i, line in enumerate(lines):
        heading = CLASS_HEADING.match(line)
        if heading:
            current = int(heading.group(1))
            continue
        if not INSTANCES_LOOSE.match(line):
            continue
        parsed = INSTANCES.match(line)
        if not parsed and i + 1 < len(lines):
            parsed = INSTANCES.match(line + " " + lines[i + 1])
        if not parsed:
            return cannot(f"line {i + 1}: an Instances line did not parse")
        if current is None:
            return cannot(f"line {i + 1}: an Instances line before any class heading")
        if current in declared:
            return cannot(f"class {current} declares Instances more than once")
        rows = [r.strip() for chunk in parsed.group(2).split(",")
                for r in chunk.split(" and ") if r.strip()]
        declared[current] = (int(parsed.group(1)), rows)
    if not declared:
        return cannot("no class Instances lines found")

    try:
        section = next(i for i, l in enumerate(lines)
                       if l.startswith("## The instances"))
    except StopIteration:
        return cannot("no '## The instances' section")
    header = next((i for i in range(section, min(section + 30, len(lines)))
                   if lines[i].startswith("| # |")), None)
    if header is None:
        return cannot("no instance table header after '## The instances'")

    table, excluded, unresolved = {}, [], []
    for line in lines[header + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            return cannot(f"table row with too few columns: {line[:48]!r}")
        row, cell = cells[0], cells[3]
        if row in table or row in excluded or row in unresolved:
            return cannot(f"row {row} appears more than once in the table")
        if cell == EXCLUDED_CELL:
            excluded.append(row)
        elif cell == UNRESOLVED_CELL:
            unresolved.append(row)
        else:
            digits = re.match(r"^(\d+)", cell)
            if not digits:
                return cannot(f"row {row}: class cell {cell!r} is neither a class "
                              "number, excluded, nor unresolved")
            table[row] = int(digits.group(1))
    if len(table) < 5:
        return cannot(f"only {len(table)} classified rows parsed; the table was "
                      "probably not read correctly")

    evidence.update(declared={c: n for c, (n, _) in sorted(declared.items())},
                    counted=len(table), excluded=excluded, unresolved=unresolved)

    problems, named_by = [], {}
    for c, (n, rows) in sorted(declared.items()):
        if n != len(rows):
            problems.append(f"class {c} says {n} but names {len(rows)} rows")
        for r in rows:
            if r in named_by:
                problems.append(f"row {r} named by class {named_by[r]} and class {c}")
            named_by[r] = c
            if r not in table:
                problems.append(f"class {c} names row {r}, not a classified table row")
            elif table[r] != c:
                problems.append(f"row {r} is class {table[r]} in the table "
                                f"but named by class {c}")
    for r, c in sorted(table.items()):
        if r not in named_by:
            problems.append(f"table row {r} (class {c}) is named by no class section")

    counted = sum(n for n, _ in declared.values())
    arithmetic = counted + len(excluded) + len(unresolved)
    if arithmetic != total:
        problems.append(f"{counted} counted + {len(excluded)} excluded + "
                        f"{len(unresolved)} unresolved = {arithmetic}, "
                        f"but the document states {total}")

    evidence["problems"] = problems
    if problems:
        return Verdict(GUARD, Outcome.FAIL, "; ".join(problems), evidence)
    return Verdict(GUARD, Outcome.PASS,
                   f"{counted} counted across {len(declared)} classes, "
                   f"{len(excluded)} excluded, {len(unresolved)} unresolved, "
                   f"total {total} as stated", evidence)
