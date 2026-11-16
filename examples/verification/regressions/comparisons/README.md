# Bundled-data relational regression

Run `python3 test.py` with installed Balsa tools and Xcelium on PATH.
`BALSA_COMPARE_TEST_DIR` selects an external artifact directory; otherwise a new
temporary directory is used. The test generates real structural Verilog and
requires simulator success plus the exact expected comparison count.

All input pairs are checked for `<`, `<=`, `>`, and `>=`: unsigned 8x8, 4x8,
8x4, and signed 8x8 and 4x8 operands. This totals 143,360 pairs and 573,440
relational results. Mixed signed/unsigned operand types are not covered.

The original `four_b_rb/BinaryFunc.abs` template forced operand B to be treated
as signed whenever implementing subtraction, including relational operations.
For unsigned variable comparisons this selected signed overflow/sign-based
decoding instead of unsigned carry-based decoding. The minimal original failure
is a=0,b=128: the generated circuit reports greater-than/greater-or-equal true.

The fix preserves the existing arithmetic subtraction path and uses the actual
input signedness for relational operators. The ALU and GCD failures were both
resolved by this mapping change without changing their input vectors or oracles.
The gate models and compiled Breeze circuits are unchanged.
