#!/bin/bash
# Full Breeze -> structural Verilog -> Xcelium flow, with external build output.
set -euo pipefail
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=${DOT_WORK_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/balsa-dot-verification.XXXXXX")}
mkdir -p "$work/generated" "$work/logs"
work=$(CDPATH= cd -- "$work" && pwd)
case "$work/" in "$source_dir/"*) echo 'Use an output directory outside the source directory.' >&2; exit 2;; esac
mode=${1:-all}
xrun=${XRUN:-xrun}
command -v "$xrun" >/dev/null || { echo 'Load the Xcelium module or set XRUN.' >&2; exit 2; }
echo "Artifacts: $work"
if ! BALSA_TEST_DIR="$work/generated" sh "$source_dir/test.sh" > "$work/logs/breeze-suite.log" 2>&1; then
    cat "$work/logs/breeze-suite.log"; exit 1
fi
cat "$work/logs/breeze-suite.log"
python3 "$source_dir/prepare_verilog.py" "$work"
(
    cd "$work/generated"
    timeout -k 5s 60s breeze2ps dot_product > "$work/logs/diagram.log" 2>&1
    test -s dot_product.ps
    timeout -k 5s 60s breeze-cost dot_product.breeze > "$work/logs/cost.log" 2>&1
)
count=$(wc -l < "$work/generated/vectors.hex")
count=${count//[[:space:]]/}
run_one() {
    local scenario=$1 status=0
    local run_dir="$work/runs/$scenario"
    local args=()
    case "$scenario" in
        elaborate) args+=(-elaborate);;
        baseline) ;;
        delayed) args+=(+DELAYED);;
        negative-mismatch) args+=(+BAD_EXPECTED);;
        negative-stall) args+=(+STALL_OUTPUT);;
        *) echo "Unknown mode: $scenario" >&2; return 2;;
    esac
    mkdir -p "$run_dir"
    (
        cd "$run_dir"
        timeout -k 5s 180s "$xrun" -64bit -sv -top dot_product_tb \
            -timescale 1ns/1ps +define+balsa_simulate +define+balsa_init_time=20 \
            -l xrun.log "$work/generated/example-cells.v" "$work/generated/dot_product.v" \
            "$source_dir/dot_product_tb.sv" "+VECTORS=$work/generated/vectors.hex" \
            "+NUM_VECTORS=$count" "+SCENARIO=$scenario" "${args[@]}"
    ) > "$run_dir/console.log" 2>&1 || status=$?
    printf '%s\n' "$status" > "$run_dir/exit-status.txt"
    if [[ "$scenario" == elaborate ]]; then
        [[ $status == 0 ]] || { tail -30 "$run_dir/console.log"; return "$status"; }
        echo 'PREPARED: Xcelium compilation/elaboration only; no HDL simulation.'
    elif [[ "$scenario" == negative-* ]]; then
        if [[ $status == 0 || $status == 124 || $status == 137 ]]; then
            echo "FAIL: $scenario did not produce expected fatal failure" >&2; return 1
        fi
        if grep -Fq 'PASS: dot-product structural Verilog' "$run_dir/console.log"; then return 1; fi
        if [[ "$scenario" == negative-mismatch ]]; then
            grep -Fq 'FAIL: injected expected-value mismatch actual=0 expected=1' "$run_dir/console.log" || { tail -30 "$run_dir/console.log"; return 1; }
        else
            grep -Fq 'INJECT: withholding result acknowledgement' "$run_dir/console.log" || { tail -30 "$run_dir/console.log"; return 1; }
            grep -Fq 'FAIL: timeout waiting result request low' "$run_dir/console.log" || { tail -30 "$run_dir/console.log"; return 1; }
        fi
        echo "PASS: checker detected $scenario"
    else
        [[ $status == 0 ]] || { tail -35 "$run_dir/console.log"; return "$status"; }
        grep -Fq "PASS: dot-product structural Verilog checked $count transactions ($scenario)" "$run_dir/console.log" || return 1
        [[ $(grep -c '^CHECK: transaction=' "$run_dir/console.log") == "$count" ]] || return 1
        grep -Fq 'COVERAGE: bit_pairs=256/256 boundaries=144/144' "$run_dir/console.log" || return 1
        if grep -Eq 'FAIL:|not correctly initialised|\*[EF],' "$run_dir/console.log"; then return 1; fi
        grep -E '^COVERAGE:|^PASS:' "$run_dir/console.log"
        echo "VERIFIED: $scenario ($count transactions)"
    fi
}
if [[ "$mode" == all ]]; then
    for scenario in baseline delayed negative-mismatch negative-stall; do run_one "$scenario"; done
    python3 "$source_dir/record_results.py" "$work"
    echo 'PASS: dot-product Breeze and Xcelium verification pipeline'
else
    run_one "$mode"
fi
