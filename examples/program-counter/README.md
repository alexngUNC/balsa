# Program-counter circuit

An original standalone example inspired by the Balsa 3.5 tutorial. Related
examples are the counters in section 3.6 (especially the loadable counter on
printed pages 43-44) and the SSEM processor's `PC`, `ZeroPC`, and `IncrementPC`
logic in section 6.6 (printed pages 74-75). This is not a copy of the SSEM CPU.

## Interface and behavior

The circuit has an 8-bit address register, initialized to zero when activated.
It accepts one command record `{operation, target}`, updates the register,
then outputs the resulting address. It waits for that output to be accepted
before receiving the next command.

| Operation | Resulting address |
| --- | --- |
| `pcReset` | 0; target is ignored |
| `pcLoad` | target (absolute jump) |
| `pcAdvance` | previous PC + 1, wrapping from 255 to 0; target is ignored |
| `pcHold` | previous PC; target is ignored |

Example transactions:

```text
{pcReset, 0}   -> 0
{pcAdvance, 0} -> 1
{pcLoad, 42}   -> 42
{pcHold, 0}    -> 42
{pcAdvance, 0} -> 43
```

This is an asynchronous, word-addressed PC, with one address per instruction.
The command handshake serves as the update event. It has no clock input,
relative branch operation, or separate asynchronous reset pin. Reset is a
command serviced between transactions. For a byte-addressed architecture with
four-byte instructions, change the increment to 4 and select the desired
address width in `PCAddress`.

Commands are bundled into one channel, as in the manual's loadable counter,
so concurrent reset/load/advance requests do not need arbitration or priority
rules. The output reports the updated PC, rather than the pre-update PC.

## Open and compile

With Balsa on `PATH`, run from the repository root:

```sh
cd examples/program-counter
balsa-mgr .
```

Select `program_counter` in the Files pane. Compile `program_counter.breeze`
from the Makefile pane. View `program_counter.ps` using the configured viewer.

Command-line equivalents:

```sh
balsa-make-makefile -b -p .
make program_counter.breeze
make ps
make cost
```

The source compiles, its circuit graph generates, and cost estimation runs.

## Simulation test

```sh
./test.sh
```

`pc_test.balsa` is a simulation-only harness that compiles with the actual
counter circuit. It exercises ten transactions: initial hold, two advances,
hold with an ignored nonzero target, load 254, advance to 255, wrap to 0,
load 42, advance to 43, and reset with an ignored nonzero target.

All ten comparisons must pass before the harness calls `BalsaSimulationStop`.
A mismatch halts the test branch without that success marker; the script
reports failure even if the simulator itself exits with status zero.

Validation completed: all ten transactions passed. A negative control that
deliberately changed an expected value correctly prevented the success marker.

### Expanded correctness audit

`test.sh` also compiles and runs `pc_exhaustive_test.balsa`. For each of the
256 possible PC states it loads that state, holds it, advances it, reloads
it, and resets it: 1,280 checked command/result transactions. This covers
hold, advance, and reset from every possible state, every load target, ignored
target fields, and the 255-to-0 boundary. A 9-bit test index avoids accidentally
wrapping the test loop itself at 255. A sticky failure bit prevents a large
number of failures from wrapping back to zero.

Both suites passed against the actual compiled circuit. Four temporary mutated
circuits (advance by 2, reset to 1, ignored load, and hold that clears PC) were
each correctly rejected by the expanded suite. The production circuit source
was unchanged during this audit.

The source review found no functional error against the documented interface.
The state starts at zero; exactly one enum operation is processed per command;
the explicit 8-bit cast implements modulo-256 increment; and the sequential
output prevents a new command from overwriting a pending result. No output
is emitted merely on initialization: issue hold or reset to obtain zero.

Backpressure is part of the interface: if the environment does not accept an
address, the circuit cannot accept another command, including reset. These
are functional simulation results and a source audit, not formal verification
or timing/physical validation. The expanded suite does not enumerate all
65,536 old-state/load-target pairs or all possible handshake schedules.

The first test harness printed intermediate values, but that exposed an
existing 64-bit crash in the simulator's string builtins (`StringAppend` /
`FormatDataGetBalsaObject`). The retained harness avoids string printing and
checks values in hardware instead; this simulator string bug remains unfixed.
The shell script prints the final pass/fail status. Synthesize only
`program_counter.balsa`, not this simulation harness.

Compiled output, netlists, and diagrams are generated locally and are not
versioned with these source files.
