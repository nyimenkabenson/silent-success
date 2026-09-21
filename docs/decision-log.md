# Decision log

Each entry records a decision, why it was made, what was rejected, and the evidence.
Entries are append-only: a reversed decision gets a new entry that supersedes the old one, never an edit.

## D-001: Classify by what a guard can observe, not by cause
- **Date:** 2026-09-20
- **Why:** The taxonomy has to produce guards, not just explanations. A cause tells you why something broke; an observable tells you what to assert. "Zero rules loaded" can come from a missing flag, an undefined variable, a wrong path, a permissions problem, a syntax error, or a version mismatch. A cause-based taxonomy scatters those across different buckets; this one puts all of them in class 1, because the guard is identical for every one: read back what actually loaded.
- **Rejected:** A cause-based taxonomy, such as the mechanism-oriented one derived from incidents in a production LLM agent runtime (arXiv 2606.14589). It would scatter one observable across several classes, so no class would map to a single guard.
- **Evidence:** `docs/taxonomy-worksheet.md` (commit 55d67d9). Demonstrated so far for one cause only, the missing config: `demos/c1_config/demo_catch.py`.

## D-002: One primary class per instance, plus recorded secondaries
- **Date:** 2026-09-20
- **Why:** The Suricata case has primary class 1, because that is the earliest point a guard could have caught it, with class 3 recorded as secondary. A taxonomy that forbids overlap cannot tell you where to intervene; one that ranks the entry points can.
- **Rejected:** Mutually exclusive classes, with no secondaries.
- **Evidence:** Worksheet rows 1 and 9. Secondary classes will be recorded in the worksheet revision pass.

## D-003: Two exclusions: incorrect success, and loud failures
- **Date:** 2026-09-20
- **Why:** Silent success means the tool says "I did it" and it did not. The Stage 6 sessionizer said "I did it" and it did, incorrectly, using the wrong algorithm. That is a bug, and counting it would turn class 3 into a bucket for every defect. A loud failure is out of scope for a different reason: the pipeline noticed it. A traceback and a non-zero exit are a signal, and silent success is defined by the absence of a signal at the interface the pipeline checks (see D-004). Row 18 excluded itself the moment the runner crashed visibly.
- **Rejected:** Counting every defect that produced a wrong result.
- **Evidence:** Worksheet rows 14 and 18.

## D-004: "Silent" means silent at the interface the pipeline checks
- **Date:** 2026-09-21
- **Why:** The pipeline acted on what it read: exit code 0 and an empty alert log. Suricata printed errors to a console the automated check never reads, so from the pipeline's point of view nothing was reported. The exit code is correct for what it documents: the engine ran. The pipeline was asking it a different question: is detection in effect? The guard exists because exit 0 cannot answer that question, not because the exit code was wrong.
- **Rejected:** Defining silent as "no error message anywhere". Suricata printed errors, yet the pipeline acted on exit code 0.
- **Evidence:** Run `demos/c1_config/demo_fail.py`, then read `out/c1/broken/console.txt`: the errors were printed, and the pipeline still saw only exit code 0.
