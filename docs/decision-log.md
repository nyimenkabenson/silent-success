# Decision log

Each entry records a decision, why it was made, what was rejected, and the evidence.
Entries are append-only: a reversed decision gets a new entry that supersedes the old one, never an edit.

## D-001: Classify by what a guard can observe, not by cause
- **Date:** 2026-09-20
- **Why:** The taxonomy has to produce guards, not just explanations. A cause tells you why something broke; an observable tells you what to assert. "Zero rules loaded" can come from a missing flag, an undefined variable, a wrong path, a permissions problem, a syntax error, or a version mismatch. A cause-based taxonomy scatters those across different buckets; this one puts all of them in class 1, because the guard is identical for every one: read back what actually loaded.
- **Rejected:** A cause-based taxonomy, such as the mechanism-oriented one derived from incidents in a production LLM agent runtime (arXiv 2606.14589). It would scatter one observable across several classes, so no class would map to a single guard.
- **Evidence:** `docs/taxonomy-worksheet.md` (commit 55d67d9). Demonstrated for two unrelated causes, both caught by the same unchanged guard: missing config (`demos/c1_config/demo.rules` with no `-c`) and a rule syntax error with the config present (`demos/c1_config/demo_syntaxerror.rules`). Both produce exit 0, zero alerts, and `rules_loaded: 0`. Suricata's error text differs between them (`rule-vars` vs `detect-sid`), so a log-text guard would have needed a second pattern; the structured-count guard needed no change.

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

## D-005: Three verdict outcomes; could-not-evaluate never counts as a pass
- **Date:** 2026-09-21
- **Why:** A boolean cannot express "I don't know", and every pipeline that forces it to ends up treating missing evidence as a pass, which is the failure this library exists to catch. The third outcome is not added complexity; it is the complexity the boolean was hiding, moved to where it can be seen. A caller who wants to treat unknown as a pass still can, but they have to write that down.
- **Rejected:** A boolean pass/fail verdict.
- **Evidence:** `guards/verdict.py`. The sabotage run of 2026-09-22 turned one refusal branch into PASS and `test_refuses_eve_without_stats` caught it.

## D-006: The class 1 guard reads eve.json stats, not the log text
- **Date:** 2026-09-21
- **Why:** The broken run never prints the "N rules successfully loaded" line at all, so a grep would find nothing, and the absence would look like success. The two causes also print different text, `rule-vars` versus `detect-sid`, so any log matcher would have to enumerate causes, which is the cause-based approach rejected in D-001. The stats event is structured, present in every run, and reports what actually loaded.
- **Rejected:** Grepping `suricata.log` for a loaded-rules line.
- **Evidence:** `out/c1/broken/console.txt` and `out/c1/correct/suricata.log`; `guards/c1_config.py`.

## D-007: Refuse a zero-rule file; refuse more than one detection engine
- **Date:** 2026-09-21
- **Why:** An empty rules file means the guard verified nothing: 0 expected and 0 loaded match, and the check passes vacuously, which is a class 5 failure inside a class 1 guard. The same logic applies to multiple detection engines, as multi-tenant Suricata produces: that configuration has not been observed here, so the guard refuses rather than guessing which engine to check. A green that means nothing is worse than a refusal that says so.
- **Rejected:** Treating zero expected and zero loaded as a pass; taking the first engine when several appear.
- **Evidence:** `test_refuses_empty_rules_file`, `test_refuses_multiple_engines`.

## D-008: A Verdict cannot be used as true or false
- **Date:** 2026-09-21
- **Why:** It refuses exactly one pattern, `if verdict:`, because Python evaluates every object as true, and on a FAIL that turns the guard's verdict into a green light. Every other use works normally: equality, explicit method calls, printing. A caller who writes `if verdict:` is asking the library to lie on their behalf, and the library won't.
- **Rejected:** Python's default object truthiness.
- **Evidence:** `guards/verdict.py`; `test_verdict_refuses_truthiness`.

## D-009: Traffic and config are generated by scripts, not committed
- **Date:** 2026-09-21
- **Why:** A committed pcap has a hash the judge takes on trust; a generated pcap has a hash the judge reproduces from the script. The config is the vendor image default plus one line, and the diff proves it: committing it would hide which parts of the evidence this project wrote and which the vendor shipped. Generating both makes the boundary visible, and a judge running `make_pcap.py` gets the exact pcap bytes produced here.
- **Rejected:** Committing a prepared pcap and a hand-written `suricata.yaml`.
- **Evidence:** `make_pcap.py` produced an identical SHA-256 across repeated runs; `make_config.py` output verified by diff against the image default, one added line.

## D-010: Demos state their claim before running, and exit 1 if the tool stops matching it
- **Date:** 2026-09-21
- **Why:** The claim is a hypothesis about how Suricata behaves given an input this project constructs: the input is controlled here, the tool's response is not. Writing the claim after seeing the output would always allow finding something in it to call success; that is the circularity worth worrying about, and fixing the claim first prevents it. Because the claim is fixed before the run, the demo can fail itself if Suricata stops producing the failure signature: it prints NOT DEMONSTRATED and exits 1, which is how this project would find out it was wrong.
- **Rejected:** Printing a results table without checking it against a stated claim.
- **Evidence:** `CLAIM` in `demos/c1_config/demo_catch.py`.

## D-011: The repository stays private until submission
- **Date:** 2026-09-21
- **Why:** What was being protected was an unfinished taxonomy from being read as a finished claim. The worksheet moved twice in two days: row 9 from class 4 to class 6, row 15 from class 1 to class 6, rows 14 and 18 from class 3 to excluded. D-001 only became evidence on 2026-09-22, when a second, unrelated cause produced the same observable and the unchanged guard caught it. A six-class taxonomy with a moving boundary is not a finding yet, it is a draft, and showing a draft as a finding is its own kind of silent success. Copying by another finalist was a partial concern, but if that were the real worry the wait would have run to the deadline rather than two days, and a six-class table is not hard to copy in any case.
- **Rejected:** Building in public from day one. Nothing material is protected by privacy: the commit history is the evidence, and the repository can be made public on request without any of it changing.
- **Evidence:** GitHub push timestamps from 2026-09-21 onward; commit history unrewritten.

## D-012: The expectation lives outside the producing script
- **Date:** 2026-09-22
- **Why:** A separate file buys the only thing that makes the check non-circular: a separate edit history. If the declaration lives in `build.py`, a change that drops an artefact edits producer and expectation in the same commit, and the guard has nothing to disagree with. `expected.txt` was committed in 504d87a, before `build.py` in ee5bf40, so the order is visible and the expectation cannot have been written after seeing the output. That is the same reason `demo_catch.py` writes its claim before running: the check is only meaningful if the two sides come from different hands, or different moments.
- **Rejected:** An `EXPECTED` constant inside `build.py`, alongside the code that produces the artefacts.
- **Evidence:** `demos/c4_evidence/expected.txt` (504d87a) precedes `demos/c4_evidence/build.py` (ee5bf40). The strongest form would be an expectation supplied from outside the build entirely, such as a CI declaration; the committed file with visible commit order is the honest approximation of that.

## D-013: The class 4 guard checks names, not counts
- **Date:** 2026-09-22
- **Why:** A count catches the three cases in the log; it does not catch the one not in the log. `report.md` renamed to `notes.md` keeps the entry count at five, so a count-based guard passes it, and that swap is a real class 4 failure: the evidence describes a different state than the real one. The complexity is not decoration, it is the cost of covering the failure a count cannot see, and the guard names which file is missing rather than only that the total is off.
- **Rejected:** Comparing the manifest's line count against an expected number.
- **Evidence:** The `swapped` case in `out/c4/results.json`: five entries, five expected, one missing (`report.md`), one unexpected (`notes.md`). Covered by `test_fail_on_swap_where_count_matches`.

## D-014: The sabotage tool refuses rather than patching best-effort
- **Date:** 2026-09-22
- **Why:** A bad injection does not produce a false pass, it produces a red run for the wrong reason, and that looks identical in the log to a sabotage that worked. If the injected line references a name the module does not import, or lands with the wrong indentation, pytest errors instead of failing, the traceback points at a NameError, and every negative-control claim resting on that run is unsupported. The tool also underpins the whole defense: the sabotage is what proves the refusal branches are load-bearing, so if the tool can report success without having done anything, nothing it certifies holds. It refuses on four conditions for the same reason the library refuses: a tool whose success signal is indistinguishable from its failure signal is the failure mode this project exists to name.
- **Rejected:** A plain string replacement with no checks.
- **Evidence:** `tools/sabotage.py`. Four refusals demonstrated on 2026-09-22: target not unique, required names absent, file untracked or dirty, file already sabotaged. Restoration is `git checkout`, which is why the tool refuses to touch anything it could not put back.

## D-015: A verdict is self-contained
- **Date:** 2026-09-24
- **Why:** The facts a verdict needed are copied into it; the paths it records are provenance, not evidence. A path is a claim about where something was, not what it was, and a guard cannot make a claim about a state it does not hold. The rule exists because four defects of the same shape appeared in succession, each in the fix for the last: a launch-time check that compared a value against itself, a verdict file overwritten by the next run, a pre-state pointer left naming the following run's record, and an output pointer naming a file the next run appends to. Every pointer to a mutable file can go stale, so a rule that closes the family is worth more than a fifth individual fix. One constraint on any such fix: closing a defect in the evidence trail must not close the failure the demo exists to reproduce. Renaming the output per run would have given each verdict an intact file to name, and would also have left no output for the next replay to append to, so the carryover would have stopped happening. The snapshot is a copy for that reason.
- **Rejected:** Recording file paths and reading them back at inspection time.
- **Evidence:** `demos/c6_carryover/replay.py` writes `pre-state-N.json`, `eve-N.json` and `verdict-N.json` under one sequence, so a verdict can only reference its own inputs. Verified by following each verdict's recorded pointers and comparing them against the verdict's own fields.

## D-016: A sabotage predicts which tests fail, not how many
- **Date:** 2026-09-24
- **Why:** The act of predicting forces a dependency model, and the diff between prediction and result is what tests that model; the sabotage itself only supplies the perturbation. Without a prediction, a red suite says something broke. With one, it says the map of what depends on what is correct or wrong, which is a different and more useful claim. Blast radius follows structure: a refusal branch is a leaf, so one branch gives one test and one red, while the alert count is a hub every verdict passes through, so sabotaging it broke five tests by construction. Two shapes of disagreement mean different things. A test predicted to fail that stays green says it never reached the path it was thought to depend on. A test that fails on a different assertion than predicted says it reaches the path but asserts something else. Both are coverage facts, not suite defects. The limit that keeps this honest: the map is only as complete as the suite, so a small blast radius can mean few things depend on this or few things are tested, and the output looks identical either way. A hub sabotage with a narrow radius is a question about missing tests, not a clean bill of health.
- **Rejected:** Treating any red suite as proof the sabotage worked.
- **Evidence:** Refusal-branch sabotages on `guards/c1_config.py`, `guards/c4_evidence.py` and `guards/c6_carryover.py` each produced exactly one failure. The counting-logic sabotage on `guards/c6_carryover.py` produced five: the two tests pinning the count, two PASS cases that flipped, and one asserting a FAIL reason the inflated count changed.

## D-017: The probe writes its own execution record
- **Date:** 2026-10-02
- **Why:** A checker that reduces "the probe exited nonzero" to "traffic was denied" cannot tell a refusal from a probe that never ran: exit 2 and exit 127 become the same safety verdict. The wrapper could special-case 127, and would then be wrong about every other exit code that means the probe did not run. The record is agnostic to why the probe is absent, which is the only property that survives contact with a cause nobody has enumerated — the same reason D-001 classifies by observable rather than by cause. The checker's output is a claim about what it believes happened; the probe's record is a trace of what did, and only a trace distinguishes the two. A verdict must be traceable to an executed probe, never inferred from its absence.
- **Rejected:** The wrapper recording whether the probe ran, from the exit code it already has.
- **Evidence:** `demos/c3_verdict/probe.py` writes a start and an end record per check; `guards/c3_verdict.py` reads them. The `unprobed` scenario in `out/c3/results.json`: three verdicts of deny, exit 127 on each, no record file written at all. The guard's claim is narrower than "the verdict is correct" — the trace proves the probe ran, not that it reached the target — and the `mismatched` scenario is where that narrowness shows: the probe ran, recorded a timeout, and a timeout does not justify a deny.

## D-018: One sabotage per load-bearing test, enforced by a sweep rather than by prose
- **Date:** 2026-10-02
- **Why:** Sabotage once per test that asserts a distinct outcome, unless several tests exercise the same code path, in which case one sabotage covers them. The rule is not one per guard, which misses branches; not one per signal, which misses conditions; and not one per return statement, which holds only when the returns have distinct tests. It is one per load-bearing test, and the tests tell you how many there are. Stated in prose this is a claim a reader has to take on trust, so it is enforced instead: `tools/sabotage_sweep.py` locates every refusal and failure branch by AST, breaks each in turn, and records which tests go red. A branch whose `tests_red` is empty is a check nothing proves can fail — class 5 inside the guards — so the sweep applies the discipline rather than only confirming it. Running it produced a distinction that reasoning had missed: a return inside the shared `cannot` helper is not a branch but the exit every refusal routes through, and sabotaging it blinds all of them at once, so helpers are measured and reported separately rather than counted against the rule.
- **Rejected:** One sabotage per guard (the earlier practice, which left most branches unproven); one per signal, as proposed before the class 3 guard was built; one per return statement.
- **Evidence:** `out/sabotage-map.json` — 38 branches and 5 helpers across 5 guards, every branch with at least one test that goes red. `verify.sh` runs the sweep with `--check` and fails if any branch has none. The sweep's `--self-test` plants a deliberately untested branch and confirms it is reported as untested; without it, a broken sweep and a library with no holes produce the same output.
