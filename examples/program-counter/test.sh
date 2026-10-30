#!/bin/sh
# Check the actual compiled handshake circuit in Breeze simulation.
set -eu
cd "$(dirname "$0")"

balsa-c -b program_counter.balsa
balsa-c -b pc_test.balsa
balsa-c -b pc_exhaustive_test.balsa
log=$(mktemp "${TMPDIR:-/tmp}/balsa-pc-test.XXXXXX")
trap 'rm -f "$log"' EXIT HUP INT TERM
if ! breeze-sim --stop-at-time=100000 pc_test > "$log" 2>&1; then
    cat "$log"
    echo "FAIL: simulator did not complete successfully" >&2
    exit 1
fi
cat "$log"
if ! grep -q 'BalsaSimulationStop called' "$log"; then
    echo "FAIL: program-counter checks did not all pass" >&2
    exit 1
fi
echo "PASS: 10 program-counter transactions"
if ! breeze-sim --stop-at-time=10000000 pc_exhaustive_test > "$log" 2>&1; then
    cat "$log"
    echo "FAIL: exhaustive simulator run did not complete successfully" >&2
    exit 1
fi
cat "$log"
if ! grep -q 'BalsaSimulationStop called' "$log"; then
    echo "FAIL: exhaustive program-counter checks did not all pass" >&2
    exit 1
fi
echo "PASS: 1280 transactions covering all 256 PC states"
