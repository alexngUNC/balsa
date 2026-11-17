#!/bin/sh
# Keep generated harnesses and Breeze artifacts outside the source checkout.
set -eu
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=${BALSA_TEST_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/balsa-dot-product.XXXXXX")}
mkdir -p "$work"
work=$(CDPATH= cd -- "$work" && pwd)
cp "$source_dir/dot_product.balsa" "$work/"
python3 "$source_dir/vectors.py" "$work" > "$work/vector-generation.log"
cd "$work"
for source in dot_product dot_test; do
    if ! timeout -k 5s 120s balsa-c -b "$source.balsa" > "$source-compile.log" 2>&1; then
        cat "$source-compile.log"
        echo "FAIL: $source compilation; artifacts: $work" >&2
        exit 1
    fi
done
if ! timeout -k 5s 180s breeze-sim --stop-at-time=1000000000 dot_test > breeze.log 2>&1; then
    cat breeze.log
    echo "FAIL: Breeze simulation; artifacts: $work" >&2
    exit 1
fi
cat breeze.log
if ! grep -q 'BalsaSimulationStop called' breeze.log; then
    echo "FAIL: missing Breeze stop marker; artifacts: $work" >&2
    exit 1
fi
echo "PASS: 816 dot-product transactions in Breeze; artifacts: $work"
