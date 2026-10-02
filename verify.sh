#!/usr/bin/env bash
# Run every demonstration and the test suite, and check the results are
# reproducible. Each demo pair is run, then its demo_catch is run a second
# time and the two results.json files are compared: determinism is verified
# here, not asserted in the README, where a quoted hash would go stale and
# could not be reproduced on another machine anyway.
#
# Exit 0 only if every demo demonstrated its claim, every result was identical
# across two runs, and every test passed.

set -u
cd "$(dirname "$0")"

PY="${PY:-python}"
fail=0
declare -a summary

step() { printf '\n=== %s ===\n' "$1"; }

check_demo() {
  local cls="$1" dir="$2"
  step "class $cls"

  if ! "$PY" "demos/$dir/demo_fail.py" > "/tmp/ss-$cls-fail.log" 2>&1; then
    summary+=("class $cls  demo_fail      DID NOT REPRODUCE (see /tmp/ss-$cls-fail.log)")
    fail=1
  else
    summary+=("class $cls  demo_fail      reproduced")
  fi
  tail -3 "/tmp/ss-$cls-fail.log"

  if ! "$PY" "demos/$dir/demo_catch.py" > "/tmp/ss-$cls-catch.log" 2>&1; then
    summary+=("class $cls  demo_catch     NOT DEMONSTRATED (see /tmp/ss-$cls-catch.log)")
    fail=1
    tail -3 "/tmp/ss-$cls-catch.log"
    return
  fi
  summary+=("class $cls  demo_catch     demonstrated")
  tail -3 "/tmp/ss-$cls-catch.log"

  # Determinism: run it again and compare the results file byte for byte.
  local results="out/c$cls/results.json"
  if [ ! -f "$results" ]; then
    summary+=("class $cls  determinism    NO RESULTS FILE")
    fail=1
    return
  fi
  local first
  first="$(sha256sum < "$results")"
  # The second run's exit code must be checked: if it failed without writing
  # results.json, the hash below would be computed against the first run's
  # file and match by definition - determinism passing because the run it was
  # meant to verify never happened.
  if ! "$PY" "demos/$dir/demo_catch.py" > "/tmp/ss-$cls-second.log" 2>&1; then
    summary+=("class $cls  determinism    SECOND RUN FAILED (see /tmp/ss-$cls-second.log)")
    fail=1
    return
  fi
  local second
  second="$(sha256sum < "$results")"
  if [ "$first" = "$second" ]; then
    summary+=("class $cls  determinism    identical across two runs  ${first:0:16}")
  else
    summary+=("class $cls  determinism    DIFFERED across two runs")
    fail=1
  fi

  # A hash says the output is stable, not that it still covers what it should.
  # The match is a plain substring, so a VALUE equal to a scenario name would
  # satisfy it as readily as a key. Good enough while scenario names are
  # distinctive; a JSON-aware check would be needed if that stops being true.
  # A demo whose own CLAIM had been narrowed would compare what remained,
  # report DEMONSTRATED and exit 0 - so the scenarios are declared outside the
  # demos and checked here.
  local want missing=()
  while IFS= read -r want; do
    case "$want" in \#*|"") continue ;; esac
    case "$want" in "$cls:"*) ;; *) continue ;; esac
    local scenario="${want#*:}"
    grep -q "\"$scenario\"" "$results" || missing+=("$scenario")
  done < demos/expected-scenarios.txt
  if [ "${#missing[@]}" -eq 0 ]; then
    summary+=("class $cls  scenarios      all declared scenarios present")
  else
    summary+=("class $cls  scenarios      MISSING: ${missing[*]}")
    fail=1
  fi
}

check_demo 1 c1_config
check_demo 3 c3_verdict
check_demo 4 c4_evidence
check_demo 6 c6_carryover

step "tests"
if test_out="$("$PY" -m pytest tests/ -q 2>&1)"; then
  summary+=("tests      $(printf '%s\n' "$test_out" | tail -1)")
else
  summary+=("tests      FAILED")
  fail=1
fi
printf '%s\n' "$test_out" | tail -3

step "summary"
printf '%s\n' "${summary[@]}"

if [ "$fail" -eq 0 ]; then
  printf '\nAll demonstrations reproduced, all results identical across two runs, all tests passed.\n'
else
  printf '\nSomething did not hold. See the lines marked above.\n'
fi
exit "$fail"
