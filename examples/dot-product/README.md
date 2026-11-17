# Four-element unsigned dot product

Both bundled-data and dual-rail structural tests are available through the
[encoding verification folders](../verification/README.md). The `verify.sh`
command below is the original bundled-data pipeline.

This original Balsa circuit computes `a0*b0 + a1*b1 + a2*b2 + a3*b3`.
Each operand is an unsigned 8-bit integer. The unsigned 18-bit result is exact:
the maximum is `4 * 255 * 255 = 260100`. Signed operands, truncation, saturation,
and configurable vector lengths are outside this example's specification.

`dot_product.balsa` defines the permanent procedure `dot4`. Each transaction
reads one `DotOperands` record, clears the accumulator, computes the result,
and sends one `DotSum`. There is no clock. Balsa cannot synthesize variable
multiplication expressions, so the circuit uses eight shift-and-add steps,
examining one multiplier bit per step. This example has no throughput or
physical timing target.

## Run the verification pipeline

With installed Balsa tools on PATH:

```sh
./test.sh
```

The runner generates a self-checking harness in an external temporary directory,
compiles the circuit and harness, and requires successful simulation exit AND
`BalsaSimulationStop called`. `BALSA_TEST_DIR` selects another external output
directory. Artifact locations are printed and retained. The tests avoid the
known string-printing builtins.

For the full structural-Verilog pipeline, also configure Xcelium and Graphviz:

```sh
# On the site where this example was verified:
module load xcelium/25.03.003
./verify.sh all
```

`DOT_WORK_DIR` selects an external output root; the default is a fresh directory
under TMPDIR or /tmp. `XRUN` selects an executable if needed. The runner performs
Breeze verification, maps the actual circuit using `example/four_b_rb`, resolves
the bundled `example-cells.v` gate/UDP models, generates a diagram and cost
estimate, and runs the SystemVerilog bench. No generated output is required in
the source checkout.

HDL modes: `baseline`, `delayed`, `negative-mismatch`, and `negative-stall`.
`all` runs all four and records accepted results and hashes in
`runtime-evidence.json`. `elaborate` compiles/elaborates without HDL simulation
and never reports functional Verilog verification. The common preparation
stages, including Breeze simulation, still run for individual modes.

## Confirmed generated protocol

The top module is `Balsa_dot4`.

| Port | Driver | Meaning |
| --- | --- | --- |
| `activate_0r` | Bench | Low during initialization, then held high for the permanent loop |
| `activate_0a` | DUT | Remains low; the procedure does not finish |
| `initialise` | Bench | Active-high initialization for generated control cells |
| `operands_0r` | DUT | Active pull request for a command |
| `operands_0a` / `operands_0d[63:0]` | Bench | Acknowledge with valid operand data |
| `result_0r` / `result_0d[17:0]` | DUT | Active push request carrying the result |
| `result_0a` | Bench | Acknowledge accepted result |

Input packing, low to high bytes: `a0,a1,a2,a3,b0,b1,b2,b3`. The bench supplies
2 ns input data setup before acknowledging the pull and holds data through
return-to-zero. It compares each result before acknowledging the push, rejects
X/Z results, and monitors output stability through request return-to-zero.
After the last result, it requires the next input request and a quiet interval
with no extra outputs.

This netlist has an explicit `initialise` input and SR flip-flop initialization
blocks. The bench asserts initialise for 20 ns, releases it, waits 20 ns, then
activates the circuit. Mapping requests `--simulation-initialise`; Xcelium
defines `balsa_simulate` and `balsa_init_time=20`. Gate models are unchanged.
Each request wait has a 10 us timeout; the bench has a 10 ms overall timeout.
The runners also enforce wall-clock timeouts. Zero exit without the expected
PASS marker is a failure. Negative tests must produce their intended fatal
messages; license errors, unrelated failures, and external timeouts do not pass.

## Coverage and observed results

`vectors.py` produces the same **816 vectors** for Breeze and SystemVerilog:

- Eight directed cases: zero, maximum, distinct lane ordering, sum above 16 bits,
  orthogonal vectors, alternating bits, and ones in either operand.
- All 256 isolated lane/bit pairs: four lanes x eight bits of A x eight bits of B.
- All 144 isolated lane boundary pairs using 0, 1, 127, 128, 254, and 255.
- 128 seeded-random cases, their operand swaps, and matching lane permutations
  (384 transactions, seed `0x0573d074`).
- Eight repetitions of maximum, maximum, zero (24 transactions).

Python integer multiplication and summation generate expected values. The HDL
bench independently checks the fixtures using native integer multiplication,
separate from the DUT's shift-and-add implementation. Coverage increments only
after the actual result and complete handshake pass.

On RHEL 8.10 with the compatibility-branch toolkit and Xcelium 25.03-s003,
these checks passed on 2026-11-15:

| Stage | Result |
| --- | --- |
| Breeze | 816 checked transactions and required stop marker |
| Netlist, diagram, cost | Generated successfully; nonempty diagram |
| Structural Verilog, nominal timing | 816 checked transactions |
| Structural Verilog, varied timing | Same 816 checked transactions |
| Wrong expected result | Intended fatal mismatch detected |
| Withheld output acknowledgement | Intended handshake timeout detected |

Each positive HDL run reached 256/256 bit-pair bins and 144/144 boundary bins:
17 maximum results, 204 results above 65535, eight identical repeated commands,
and eight zero-after-maximum results. Delayed mode uses a fixed LCG seed with
1–23 ns input responses, 1–31 ns output backpressure, and 1–7 ns return-to-zero
holds. Nominal mode uses 1 ns responses and 2 ns holds.

This is functional simulation coverage for the stated vectors and schedules.
It is not exhaustive over all 64-bit input records, a formal equivalence proof,
or physical timing validation. Gate delays and area cost estimates belong to
the bundled example technology.
