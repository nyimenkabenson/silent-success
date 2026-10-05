# The silent-success taxonomy

Six classes of failure in security tooling, the guard principle for each, and the
twenty-seven instances the classification was built from.

## What silent success is

A tool claims to have done work it did not do. The claim is what makes it silent:
the tool reports, and the report is wrong.

**Silent means silent at the interface the pipeline checks.** Suricata prints errors
to a console an automated check never reads; from the pipeline's point of view,
nothing was reported. A failure a human could have seen in a terminal is still
silent if the thing consuming the result could not.

Two things fall outside the class, and both are kept in the table below so the
boundary is visible rather than asserted:

- **Incorrect success** — the tool did the work, with the wrong algorithm. Row 14:
  the Stage 6 sessionizer produced sessions for every event, using a 60-second
  time-gap rule that was wrong. It said "I did it" and it did, incorrectly. That is
  a bug. Counting it would turn class 3 into a bucket for every defect.
- **Loud failure** — the tool crashed visibly. Row 18: a fixture runner raised after
  writing its output, with a traceback and a non-zero exit. The pipeline noticed. A
  signal, not silence.

## Inclusion criteria

The criteria are borrowed, not invented. They are from Li, Fan and Zhuang,
*Auditing the Audit: Five Failure Modes in Benchmark-Validity Audits*
(arXiv:2607.02586v1, preprint, 1 July 2026). A failure is in scope only if it is:

- **(C1) silent** — invisible in the reported numbers, so a reader cannot detect it
  from the evidence artefact alone;
- **(C2) realized** — actually encountered, not hypothesised;
- **(C3) gateable** — it maps to a concrete, checkable assertion.

All three are adopted here and applied to security tooling rather than to
benchmark-validity audits. The paper names C1 as load-bearing and puts loud failures
out of scope as "a software-quality problem, not an evidence-trust problem", which is
the same boundary this taxonomy reaches from its own instances.

**Two things are changed in the transfer.**

*The axis.* The paper classifies by pipeline role — silent no-op perturbation, regex
extraction artefact, non-faithful scoring. This taxonomy classifies by **observable**,
because it exists to produce guards and a guard can only assert on what it can read.
One observable arises from many causes: "zero rules loaded" can come from a missing
flag, an undefined variable, a wrong path, a permissions problem, a syntax error or a
version mismatch, and one unchanged guard catches all of them. A cause-based axis
would scatter those across classes, and no class would map to a single guard. See
D-001.

*The gate.* The paper maps each class to a due-diligence disclosure an evidence
consumer could demand. This taxonomy maps each class to a guard returning `PASS`,
`FAIL` or `CANNOT_EVALUATE`, whose refusal branches are load-bearing. Their gate is a
document; this one is executable.

**One divergence, named rather than smoothed over.** The paper's C1 defines silent as
invisible to a governance reader. This taxonomy defines it as silent at the interface
the pipeline checks, even where a human-readable error exists. These are compatible
but not identical: in the degraded Suricata run, three `Error:` lines were printed, so
by the paper's C1 a reader with the console could see it, while by the definition used
here it is silent because the pipeline read only the exit code. The definition used
here is the broader one.

## The classes

Five classes map to a guard principle; four of those principles are implemented as
code. Class 5 maps to no guard at all, and is described separately below.

| # | Class | Guard principle | Code |
|---|---|---|---|
| 1 | Config not in effect | Read back what the running tool actually loaded | `guards/c1_config.py`, `guards/c1_engine_config.py` |
| 2 | Accepted, not processed | Assert on extraction, not on acceptance | none |
| 3 | Error turned into a verdict | A verdict must be traceable to an executed probe | `guards/c3_verdict.py` |
| 4 | Evidence doesn't match reality | Check against an expectation that does not come from the thing being checked | `guards/c4_evidence.py` |
| 6 | Carryover from a prior run | Prove the starting state is empty before running | `guards/c6_carryover.py` |

### Class 1 — Config not in effect

The tool runs, but not with the configuration it was given.

**Instances: 4** (rows 1, 4, 5, S1), all reproducible with public tools.
**Guards: two, both implemented.** `c1.suricata_rules_in_effect` reads the effective
rule count from `eve.json` stats; `c1.engine_config_read` reads the engine's own log
for configuration-file problems.

Two guards for one class because one observable does not cover the other. The
degraded run in S1 loaded its rule, alerted once, and exited 0 — so the rules guard
**passes** it — while three of Suricata's own configuration files were unreadable, which
only the engine guard sees. A guard answers the question it was built for and says
nothing about the one it was not. Both are demonstrated live in
`demos/c1_config/demo_catch.py`.

### Class 2 — Accepted, not processed

The tool takes the input and pulls nothing usable out of it.

**Instances: 1** (row 2), reproducible with public tools.
**Guard principle:** assert on extraction, not on acceptance.
**Code: none.**
**Why catalogued:** one instance is an observation, not a pattern. The single case —
a Wazuh decoder whose prematch claimed the line while its OS_Regex negated classes
extracted no fields — needs the Wazuh stack, which is the heaviest environment tier
and the one this project does not ship. It is a class rather than a footnote because
it meets all three criteria: it was silent at the interface checked, it was realized
rather than hypothesised, and it is gateable — "assert on extraction, not acceptance"
is a concrete check someone could write. The taxonomy is descriptive, so a class needs
an instance and a checkable assertion, not a demonstration.

### Class 3 — Error turned into a verdict

A failure to evaluate becomes a valid-looking result.

**Instances: 4** (rows 3, 7, 17, S6); rows 3 and S6 are reproducible with public
tools, rows 7 and 17 as a pattern rather than as the original incident.
**Guard: implemented.** `c3.verdict_traceable_to_probe` judges a verdict against the
probe's own execution record.

A checker that reduces "the probe exited nonzero" to "traffic was denied" cannot tell a
refusal from a probe that never ran: exit 2 and exit 127 become the same safety verdict.
The checker's output is a claim about what it believes happened; the probe's record is a
trace of what did, and only a trace distinguishes the two. A verdict must be traceable to
an executed probe, never inferred from its absence. See D-017.

The claim is narrower than "the verdict is correct": the trace proves the probe ran, not
that it reached the target. A probe that ran and recorded a timeout still has no evidence
about whether the port is blocked, which is why the `mismatched` scenario fails rather
than passes.

The `unprobed` scenario is a class 1 failure — the probe binary is not in effect —
surfacing as a class 3 verdict, a deny with no trace. The guard catches the class 3
symptom because that is the observable; the class 1 cause is upstream and outside this
guard's scope. Two of the four instances are classified on reasoning rather than on a
recovered log (see the Status column).

### Class 4 — Evidence doesn't match reality

An artefact describes a different state than the one claimed.

**Instances: 6** (rows 8, 10, 13, 16, S3, S4); five reproducible with public tools,
row 13 as a pattern.
**Guard: implemented.** `c4.manifest_covers_expected` compares a manifest against a
declaration of expected artefacts that the build does not produce.

A hash proves the files you know about are intact. It cannot prove you know about all
of them: **absence has no hash.** So the guard checks names, not counts — a count
passes the case where `report.md` is renamed to `notes.md` and the total stays at
five. The expectation lives outside the producing script, with its own commit history,
so a change that drops an artefact cannot update producer and expectation in one
edit. See D-012 and D-013.

### Class 5 — Passed for the wrong reason

The check is green but is not measuring what it claims.

**Instances: 5** (rows 6, 11, 12, S2, S5).

**This class has no guard, and that is a property of the class rather than a gap.**
Its countermeasure is a discipline: every guard ships with a negative control that
proves it can go red. `tools/sabotage.py` breaks one branch at a time and the suite
must fail — and must fail the *predicted* tests, not merely some. A refusal branch is
a leaf and turns exactly one test red; the alert-count path in class 6 is a hub every
verdict passes through, so sabotaging it turned five red by construction. The diff
between prediction and result is what tests the dependency model; the sabotage only
supplies the perturbation. See D-016.

That discipline is also the reason this class is self-referential: row 11 is thirty
green tests over broken sensor evidence, S2 is a launch-time check that compared a
value against the call it came from, and S5 is a sabotage tool that did nothing when
its target text did not match. Each is a check that could only ever pass.

The discipline is enforced rather than asserted. `tools/sabotage_sweep.py` locates every
refusal and failure branch in every guard by AST, breaks each one in turn, and records
which tests go red; `verify.sh` runs it with `--check` and fails if any branch has none.
`verify.sh` generates the map at `out/sabotage-map.json`, which is gitignored, so a fresh
clone has it after the first run: 38 branches and 5 shared `cannot` helpers across 5
guards, every branch load-bearing. A branch with an empty `tests_red` would be this class
inside the guards themselves - a check nothing proves can fail - so the sweep is not only
confirming the discipline but applying it. The sweep ships with a self-test that plants a
deliberately untested branch and confirms it is reported as untested, because a broken
sweep and a library with no holes produce the same output.

**The limit worth stating:** the blast radius of a sabotage is only as complete as the
suite. A narrow radius can mean few things depend on this, or few things are tested,
and the output looks identical either way. A hub sabotage with a narrow radius is a
question about missing tests, not a clean bill of health.

### Class 6 — Carryover from a prior run

State from an earlier run survives into the next and corrupts it.

**Instances: 3 counted** (rows 9, 15, 19), all reproducible with public tools; row 20
is unresolved and excluded from the count.
**Guard: implemented.** `c6.output_free_of_prior_runs` checks a recorded pre-run state
together with a declared event count.

**This class breaks an assumption the others rest on.** Classes 1 and 4 judge a run
from evidence inside it. Class 6 cannot: run two, in isolation, is indistinguishable
from a healthy run one. The failure is an absence — of a clean slate — and absence is
only visible against a before. The count alone distinguishes nothing, since excess
events are equally consistent with carryover, a larger input, or a rule firing twice.
The recorded pre-state is what rules carryover in or out.

**Class 6 requires one trusted fact.** The pre-state is a claim made by the wrapper,
and the guard cannot independently verify it afterwards. Any record the wrapper makes
is a claim by a component of the system being verified; git commits, external watchers
and tamper-evident logs move that trust rather than removing it. What is possible is
to make the claim falsifiable at launch — the wrapper refuses if `--clean` was given
and the output still exists — and to state the residual trust rather than dress it up.
The strongest available form is a run-scoped output path under a nonce the judge
supplies, where freshness stops being the project's claim to make.

## The instances

Twenty-six rows. **Reproducible?** says what a reader can rebuild: `Yes` with public
tools, `Pattern` where the specific incident is not shareable but the failure mode
reproduces in a fresh fixture, `No` where it cannot be reconstructed. **Status** says
what the classification rests on.

Five rows reference programme material that cannot be published. They are included
because the taxonomy is descriptive, not only demonstrative: a class does not require
every instance to be publicly reproducible. The demonstrated classes rest on publicly
reproducible instances; the programme rows are supporting evidence.

| # | Incident | Source | Class | Reproducible? | Status |
|---|---|---|---|---|---|
| 1 | Suricata `-S` without `-c`: zero rules loaded, exited clean | Stage 7 / 9B | 1 (sec. 3) | Yes | resolved |
| 2 | Wazuh decoder claimed the line but extracted no fields | Stage 8 | 2 | Yes | resolved |
| 3 | Wazuh certs generator failed silently, left certs at mode 0500 | Stage 8 | 3 | Yes | provisional |
| 4 | Config overlays installed where Docker Compose never reads them | Stage 8 | 1 | Yes | resolved |
| 5 | `docker compose restart` did not reload config | Stage 8 | 1 | Yes | resolved |
| 6 | Fixture runner judged UDP by matching rule comment text | Stage 7 | 5 | Pattern | resolved |
| 7 | Unknown source zone: the command failed, got scored "deny" | Stage 7 | 3 | Pattern | resolved |
| 8 | `manifest.sha256` built after `make clean`: 74 lines, not 85 | Stage 7 | 4 | Yes | resolved |
| 9 | `.pytest_cache` listed a renamed test as failed | Stage 7 | 6 | Yes | resolved |
| 10 | `eve.json` kept growing after it was hashed | Stage 7 | 4 | Yes | resolved |
| 11 | Path bug broke sensor evidence; all 30 matrix tests stayed green | Stage 7 | 5 | Pattern | resolved |
| 12 | Four fields in the Stage 8 replay that gave away the answer | Stage 8 | 5 | No | resolved |
| 13 | capture-log said 3 rules loaded; the log said 0 | Stage 9B | 4 | Pattern | resolved |
| 14 | Stage 6 sessionizer produced wrong sessions | Stage 6 | **excluded** | No | resolved |
| 15 | `docker image rm` did not force a real rebuild | Stage 7 | 6 (sec. 4) | Yes | resolved |
| 16 | `git add -A` after clean silently untracked deliverables | Stage 7 | 4 | Yes | resolved |
| 17 | Parallel `apk add` left the gateway without nftables | Stage 7 | 3 | Pattern | provisional |
| 18 | Fixture runner crashed after writing its output | Stage 7 | **excluded** | Pattern | resolved |
| 19 | `eve.json` appended across replays: run 2 includes run 1's events | Stage 7 / 9B | 6 | Yes | resolved |
| 20 | A leftover clean-room lab blocked the next lab on a fixed name | Stage 7 | — | Yes | **unresolved** |
| S1 | `--user` left Suricata unable to read three config files; `verify.sh` green | 9B build | 1 | Yes | resolved |
| S2 | `replay.py` launch check compared a value against the call it came from | 9B build | 5 | Yes | resolved |
| S3 | `demo_catch` dropped replays that wrote no verdict from its table | 9B build | 4 | Yes | resolved |
| S4 | `verdict-N` named a pre-state file the next run had overwritten | 9B build | 4 | Yes | resolved |
| S5 | `sabotage.py` did nothing when its target text did not match | 9B build | 5 | Yes | resolved |
| S6 | `$?` after a pipeline reported grep's status, masking `verify.sh`'s exit 1 | 9B build | 3 | Yes | resolved |
| S7 | `verify.sh` reported the sweep's refusal to run as a named finding about the guards | 9B build | 3 | Yes | resolved |

### Rows that are not settled

**Row 20 is unresolved and excluded from the class counts.** If containerlab refused
with an error, it is a loud failure and a third exclusion. If the clean-room tests
instead ran against the lab that was still up, it is class 6 and a strong one. Nobody
has checked which, so it is not classified on a guess.

**Rows 3 and 17 are classified on reasoning, not on a recovered log.** Row 3: the
certs generator's permissions step did not run and the generator reported success
regardless; whether `find: command not found` was printed affects how loud it was, not
what the verdict said, and the pipeline read the exit code. Row 17: `apk` failed and
containerlab reported the lab deployed — a failing sub-step under a parent that
reports success, the same shape as S6. Both arguments are sound and neither is
evidence; the Status column says so.

### The S rows

Rows S1 to S6 are failures created during the building of this project, not inherited
from the programme stages. They are included deliberately. Li, Fan and Zhuang record,
per failure, whether it was inherited from the initial pipeline or introduced during
repair, and their most diagnostic case — a scorer-truncation bug — was one they
introduced while fixing another. Theirs produced plausible publishable numbers before
anyone inspected the right thing.

S1 is the same shape and is the sharpest instance in this catalogue: a flag added that
morning to fix a file-ownership annoyance left Suricata unable to read three of its own
configuration files, and `verify.sh` reported every demonstration reproduced, every
result identical across runs, and all tests passing. The evidence is the console log.
That incident is why `c1.engine_config_read` exists, and why the class 1 demonstration
now runs the degraded case live as a third scenario.

**Six of the seven sit in the verification layer**, across five categories: the sabotage
tool (S5), the demo's own report (S3), the evidence trail (S2 and S4), the shell command
used to test a check (S6), and the verification script's own reporting (S7). Only S1 is
in the artefact itself. That clustering is the finding: the code that verifies is where
this failure class concentrates, because nobody verifies the verifier.

## What is not claimed

- **The six classes are not a complete partition** of silent success in security
  tooling. They are the classes the realized instances supported.
- **Two classes have no guard.** Class 2 has one instance. Class 5 is a discipline
  rather than an assertion. Neither is described as planned work; what exists is what
  is listed.
- **The instance set is one practitioner's,** gathered across one programme and one
  build. Its calibration across other codebases is untested.
- **Two guards rest on something the guard cannot verify:** class 6's pre-state record,
  and class 1's engine-config guard, whose positive half can only require confirmations
  that Suricata chooses to print. A configuration file that failed in a form producing
  no error line and no missing confirmation would not be caught. The split between what
  can be confirmed and what can only be denied is stated in the guard's docstring.

Every design decision behind the above, with its rejected alternative and its evidence,
is in [decision-log.md](decision-log.md).
