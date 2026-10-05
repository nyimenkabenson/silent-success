# Silent Success

**An unplugged smoke alarm looks exactly like a smoke alarm with nothing to report.**

Security tools report "nothing found" — and you cannot tell whether that means nothing was
there, or the tool never actually looked. A detection engine that loaded zero rules exits with
the same status code, and the same empty alert log, as one that ran perfectly and found nothing.

This project names that failure class, classifies it, and ships guards that check a tool
*did the work* rather than that it exited zero — for four of the six classes so far.

## What this is

A taxonomy of **silent success** in security tooling. Four of the six classes ship a guard
and a reproducible demonstration of that guard catching a tool reporting success while having
done nothing; the other two are catalogued, with their guards specified but not built.

Every guard returns one of three outcomes — `PASS`, `FAIL`, or `CANNOT_EVALUATE` — and none of
the refusal paths can become a pass. A guard that cannot find its evidence says so; "I could not
check" is never recorded as "it is fine".

## Silent success, defined

A tool claims to have done work it did not do. The claim is what makes it silent: the tool
reports, and the report is wrong.

Two things fall outside:

- **Incorrect success** — the tool did the work with the wrong algorithm. A bug, not a lie.
- **Loud failure** — the tool crashed visibly. A signal, not silence.

Silent means silent *at the interface the pipeline checks*. Suricata prints errors to a console
an automated check never reads; from the pipeline's point of view, nothing was reported.

## Run it

First time:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then, with the environment active:

```bash
./verify.sh
```

Runs every demonstration, checks each result is byte-identical across two runs, and runs the
test suite. Needs Python 3.12+ and Docker.

Or the five-minute version:

```bash
python demos/c1_config/demo_fail.py # exit 0, zero alerts, CLEAN
python demos/c1_config/demo_catch.py # the naive check passes both runs; the guard fails one
cat out/c1/broken/console.txt # the errors Suricata printed while exiting 0
```

That is the whole thesis in ninety seconds.

## The classes

| # | Class | Guard | Status |
|---|---|---|---|
| 1 | Config not in effect | read back what the tool actually loaded | demonstrated, two guards |
| 2 | Accepted, not processed | assert on extraction, not acceptance | catalogued |
| 3 | Error turned into a verdict | pass, fail, or could-not-evaluate | demonstrated |
| 4 | Evidence doesn't match reality | check against an independent declaration | demonstrated |
| 6 | Carryover from a prior run | prove the starting state is empty | demonstrated |

*demonstrated* means a working guard, a failure that reproduces on demand, and a catch
that is tested. *catalogued* means instances recorded and the guard named, not built.

A sixth class — **passed for the wrong reason** — has five instances and no guard, because
its countermeasure is a discipline rather than an assertion: every guard here ships with a
negative control that proves it can go red. See the taxonomy for why that is a property of
the class and not a gap.

Incidents, reasoning and the boundary criteria: [docs/taxonomy.md](docs/taxonomy.md).
Every design decision, with its rejected alternative: [docs/decision-log.md](docs/decision-log.md).

## Why believe the classes are real

They came from incidents lived on this project, not from a literature review — the Suricata flag,
the decoder that claimed a line and extracted nothing, `restart` versus `--force-recreate`,
hashing after `make clean`.

The classification axis is **what a guard can observe**, not why the failure happened, because the
taxonomy exists to produce guards. Class 1 shows why: an undefined config variable and a rule
syntax error have nothing in common as causes, but both produce `rules_loaded: 0`, and one
unchanged guard catches both.

Four of the five classes in the table have live demonstrations against real tools,
deterministic across runs. The fifth is catalogued, and the table says which is which.
Class 5, outside the table, has no guard by design.

Every guard's refusal branches have negative controls: `tools/sabotage.py` breaks one branch at a
time and the suite must go red. It refuses to run against a file it could not restore.

## Limitations

- **Class 6 requires one trusted fact.** The guard reads a pre-run state recorded by the wrapper,
  and cannot independently verify that record afterwards. The record is produced by code in this
  repository, which anyone can read.
- **Suricata's output has no stable byte-level property.** `flow_id` is assigned per invocation, so
  two replays of the same pcap differ in bytes and in length. Only packet-derived values are
  recorded.
- **Determinism is verified across checkouts, not across machines.** `verify.sh` asserts that two
  runs within one invocation produce identical results. On 2026-10-05 a clean clone at a different
  path reproduced the same per-class hashes as the working copy, which rules out dependence on the
  path, the checkout, or leftover output, and shows the recorded results contain no absolute paths.
  All of it ran on one machine, one kernel and one Suricata image. A different machine may produce
  different hashes; nothing here tests that.
- **One replay failed to complete, once, and has not reproduced.** It wrote its pre-state and died
  before its verdict. The demo now shows a replay that produced no verdict rather than omitting it.
- **`verify.sh` has a demonstrated blind spot.** On 2026-09-29 it reported everything green while
  Suricata was failing to read three of its own configuration files: a `--user` flag added that
  morning left the container unable to open them, and Suricata degraded, still loaded the rule,
  still alerted, still exited 0. Every demo, every guard and all 70 tests passed. The evidence is
  in the console log. A verification script is not exempt from the failure class it verifies.

  The flag was reverted the same day, and a guard now covers it: `c1.engine_config_read`
  reads Suricata's own log and fails when the engine reports it could not open a
  configuration file, or when a confirmation it should have printed is absent. The class 1
  demonstration runs the degraded case live as its third scenario — the rules guard passes
  that run, and only the engine guard catches it. The blind spot is now covered by the
  guard whose absence let it through.
