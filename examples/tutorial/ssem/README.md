# Manual example: Manchester SSEM processor

`ssem.balsa` is a faithful transcription of section 6.6 of the Balsa 3.5
manual, printed pages 73-75 (PDF pages 81-83). The complete processor listing
is assembled from the separate types, declarations, helper procedures, decode
procedure, and main-body blocks. Formatting and comments are adjusted; no
circuit behavior was changed. It compiles with the installed Balsa 4.0.

## What the circuit contains

This is the complete small processor example, including its PC, rather than
an extracted standalone PC. It has a 32-bit accumulator, 32-bit instruction
word, 5-bit PC, and a memory interface:

| Port | Meaning |
| --- | --- |
| `MemA` | 5-bit memory address |
| `MemRNW` | 1 for read, 0 for write |
| `MemR` | 32-bit value received from memory |
| `MemW` | 32-bit value sent to memory |
| `halted` | Handshake issued on STOP |

The instruction set includes JMP, JRP, LDN, STO, SUB (two encodings), TEST,
and STOP. The memory model is external to the processor, as in the manual.
The PC starts at zero and increments before each instruction fetch, so the
first instruction comes from address 1. After JMP assigns PC to a value, the
next fetch increments that value first.

The `CRTNo` field is retained from the manual, but this implementation uses
only the five-bit line address. Instruction bits are defined by the
`SSEMInst` record: line address in bits 0-4, CRT number in bits 5-12,
and function in bits 13-15, over the 32-bit word.

The source initializes `ACC`, `PC`, and `Stopped` explicitly, as printed.
It does not explicitly initialize `ACC_slave`; the test program starts with
LDN, which sets the accumulator result before its use. No extra reset behavior
has been silently added to the transcription.

## Open and build

With Balsa on `PATH`, run from the repository root:

```sh
cd examples/tutorial/ssem
balsa-mgr .
```

Select `ssem`, then compile `ssem.breeze` in the Makefile pane. The procedure
name is `SSEM`. The `ssem.ps` graph is much larger than the first buffer graph.

Command-line equivalents:

```sh
balsa-make-makefile -b -p .
make
make ps cost
./test.sh
```

## Simulation test

`ssem_test.balsa` supplies an original deterministic memory environment and
test program. It is not the GCD memory example mentioned later in the manual.
It checks every address and read/write direction across 12 memory transactions:

| Instruction address | Instruction / effect |
| --- | --- |
| 1 | LDN [20], with memory[20] = 5: ACC becomes -5 |
| 2 | SUB [21], with memory[21] = 3: ACC becomes -8 |
| 3 | STO [22]: verify the stored 32-bit value is -8 |
| 4 | TEST: negative ACC skips address 5 |
| 6 | JRP [23], with memory[23] = 1: next fetch is address 8 |
| 8 | JMP [24], with memory[24] = 9: next fetch is address 10 |
| 10 | STOP: verify the halted handshake |

Compilation, graph generation, cost estimation, and this simulation passed.
The test calls `BalsaSimulationStop` only when the checks passed; `test.sh`
requires that marker and reports a missing marker as failure. The harness
avoids the known simulator string-printing crash. This test exercises the
seven instruction behaviors above, not every possible program, SUB_alt
encoding, PC-wrap condition, or hardware implementation.

The circuit and its original test harness are included as source; regenerate
compiled output, netlists, and diagrams locally.
