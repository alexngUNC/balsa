# Bundled-data relational regression

Run `python3 test.py` with installed Balsa tools and Xcelium on PATH.
`BALSA_COMPARE_TEST_DIR` selects an external artifact directory; otherwise a new
temporary directory is used. The test generates real structural Verilog and
requires simulator success plus the exact expected comparison count.

All input pairs are checked for `<`, `<=`, `>`, and `>=`: unsigned 8x8, 4x8,
8x4, and signed 8x8 and 4x8 operands. This totals 143,360 pairs and 573,440
relational results. Those exhaustive cases use matching input signedness.
Mixed-sign boundary coverage is provided by the separate runner below.

The original `four_b_rb/BinaryFunc.abs` template forced operand B to be treated
as signed whenever implementing subtraction, including relational operations.
For unsigned variable comparisons this selected signed overflow/sign-based
decoding instead of unsigned carry-based decoding. The minimal original failure
is a=0,b=128: the generated circuit reports greater-than/greater-or-equal true.

The fix preserves the existing arithmetic subtraction path and uses the actual
input signedness for relational operators. The ALU and GCD failures were both
resolved by this mapping change without changing their input vectors or oracles.
The gate models and compiled Breeze circuits are unchanged.

## Mixed-sign boundary regression

Run `nice -n 15 python3 boundary_test.py` with Balsa and Xcelium on PATH.
The runner uses one-CPU affinity and executes configurations sequentially.
Generated files use an external temporary directory. Set
`BALSA_COMPARE_TEST_DIR` to retain them at a chosen external location.

The test checks 49 boundary pairs for each operand configuration, using u8/s8,
s8/u8, u4/s8, s4/u8, u8/s4 and s8/u4. Here u denotes unsigned and s denotes
signed. Both bundled-data and dual-rail mappings are simulated, giving 588
pairs and 2352 relational results. Each generated Breeze self-check must reach
its simulation-stop marker. Xcelium completes each selected pair and reports
every mismatch. Any failing configuration makes the runner exit nonzero.

`MIXED_SIGN_MODE=controls` selects matching-sign configurations with the same
widths and boundary values. `MIXED_CASE_FILTER=u8_s8` restricts a mixed-sign
run to the indicated operand pair. With `BALSA_COMPARE_TEST_DIR` pointing at
an existing run, `--results-only` checks saved verdicts without simulation.

These tests exposed additional operand-extension defects. Bundled-data mapping
used the one-bit result width when deciding whether mixed operands required an
extra comparison bit. It also filled an inverted wide unsigned B operand with
the wrong extension bit. Dual-rail mapping similarly omitted relational-input
inversion when extending the wide unsigned operand. The templates now account
for the operand range and the inversion state.

The mixed-sign boundary matrix and matching-sign boundary controls passed with
the corrections. This is directed boundary coverage for the listed widths.
