#!/bin/sh
# Check the actual compiled handshake circuit in Breeze simulation.
set -eu
cd "$(dirname "$0")"

balsa-c -b count10b.balsa
balsa-c -b counter_test.balsa
log=$(mktemp "${TMPDIR:-/tmp}/balsa-manual-test.XXXXXX")
trap 'rm -f "$log"' EXIT HUP INT TERM
if ! breeze-sim --stop-at-time=100000 counter_test > "$log" 2>&1; then
    cat "$log"
    echo "FAIL: simulator did not complete successfully" >&2
    exit 1
fi
cat "$log"
if ! grep -q 'BalsaSimulationStop called' "$log"; then
    echo "FAIL: manual-example checks did not all pass" >&2
    exit 1
fi
echo "PASS: 10 manual-counter transactions"
