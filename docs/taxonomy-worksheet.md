# First classification pass, 2026-09-20

**Superseded snapshot. Not the current classification.** This is the first pass, written
before the review that produced the classes in `taxonomy.md`. It is kept unedited as
provenance, so the classification can be audited as it developed rather than only as it
ended up. The table below is the original file's bytes, CRLF line endings and all.

Four rows were left open here and are resolved or restated in `taxonomy.md`: rows 3, 7
and 17 are marked pending a log check, and row 20 is marked pending and points to a note
below it that was never written.

For current classes and statuses, the two exclusions, and the six instances introduced
during the build, read [`taxonomy.md`](taxonomy.md). Cited as evidence in D-001.

```text
#	What happened	Class	Public
1	Suricata -S without -c: zero rules loaded, exited clean	1	Yes
2	Wazuh decoder claimed the line but extracted no fields	2	Yes
3	Wazuh certs generator failed silently, left certs at mode 0500	3 (pending log check)	Yes
4	Config overlays installed where Docker Compose never reads them	1	Yes
5	docker compose restart didn't reload config	1	Yes
6	Fixture runner judged UDP by matching rule comment text	5	Yes
7	Unknown source zone: the command failed, got scored "deny"	3 (pending log check)	Yes
8	manifest.sha256 built after make clean: 74 lines, not 85	4	Yes
9	.pytest_cache listed a renamed test as failed	6	Yes
10	eve.json kept growing after it was hashed	4	Yes
11	Path bug broke sensor evidence; all 30 matrix tests stayed green	5	Yes
12	Four fields in the Stage 8 replay that gave away the answer	5	Partial
13	capture-log said 3 rules loaded; the log said 0	4	Yes
14	Stage 6 sessionizer produced wrong sessions	Exclude — incorrect success, plain bug	N/A
15	docker image rm didn't force a real rebuild	6 (secondary 4)	Yes
16	git add -A after clean silently untracked deliverables	4	Yes
17	Parallel apk add left the gateway without nftables	3 (pending log check)	Public, non-deterministic
18	Fixture runner crashed after writing its output	Exclude — loud failure	N/A
19	eve.json appended across replays	6	Yes
20	Leftover lab blocked the next lab on netforge-a3	Pending — see below	Unsure
```
