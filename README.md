# Silent Success

**An unplugged smoke alarm looks exactly like a smoke alarm with nothing to report.**

Security tools report "nothing found" — and you cannot tell whether that means nothing was
there, or the tool never actually looked. A detection engine that loaded zero rules exits with
the same status code, and the same empty alert log, as one that ran perfectly and found nothing.

This project names that failure class, classifies it, and ships a guard for each class that
checks a tool *did the work*, rather than that it exited zero.

## What this is

A taxonomy of **silent success** in security tooling, with a guard for each class and a
reproducible demonstration of each guard catching a real tool in the act.

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

./verify.sh

Runs every demonstration, checks each result is byte-identical across two runs, and runs the
test suite. Needs Python 3.12+ and Docker.

Or the five-minute version:

python demos/c1_config/demo_fail.py # exit 0, zero alerts, CLEAN
python demos/c1_config/demo_catch.py # the naive check passes both runs; the guard fails one
cat out/c1/broken/console.txt # the errors Suricata printed while exiting 0

That is the whole thesis in ninety seconds.

## The classes

| # | Class | Guard | Status |
|---|---|---|---|
| 1 | Config not in effect | read back what the tool actually loaded | demonstrated |
| 2 | Accepted, not processed | assert on extraction, not acceptance | catalogued |
| 3 | Error turned into a verdict | pass, fail, or could-not-evaluate | catalogued |
| 4 | Evidence doesn't match reality | check against an independent declaration | demonstrated |
| 5 | Passed for the wrong reason | every guard needs a negative control | catalogued |
| 6 | Carryover from a prior run | prove the starting state is empty | demonstrated |

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

Three classes have live demonstrations against real tools, deterministic across runs. The other
three are catalogued instances with named guards, and the table above says which is which.

Every guard's refusal branches have negative controls: `tools/sabotage.py` breaks one branch at a
time and the suite must go red. It refuses to run against a file it could not restore.

## Limitations

- **Class 6 requires one trusted fact.** The guard reads a pre-run state recorded by the wrapper,
  and cannot independently verify that record afterwards. The record is produced by code in this
  repository, which anyone can read.
- **Suricata's output has no stable byte-level property.** `flow_id` is assigned per invocation, so
  two replays of the same pcap differ in bytes and in length. Only packet-derived values are
  recorded.
- **One replay failed to complete, once, and has not reproduced.** It wrote its pre-state and died
  before its verdict. The demo now shows a replay that produced no verdict rather than omitting it.
- **`verify.sh` has a demonstrated blind spot.** On 2026-09-29 it reported everything green while
  Suricata was failing to read three of its own configuration files: a `--user` flag added that
  morning left the container unable to open them, and Suricata degraded, still loaded the rule,
  still alerted, still exited 0. Every demo, every guard and all 48 tests passed. The evidence is
  in the console log. A verification script is not exempt from the failure class it verifies.
