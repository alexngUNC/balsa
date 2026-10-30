# Manual example: loadable up/down decade counter

`count10b.balsa` is a faithful transcription of the circuit listing in section
3.6 of the Balsa 3.5 manual, printed pages 43-44 (PDF pages 51-52). Only
formatting and comments have changed; the types, names, and behavior are kept.
No compiler compatibility changes were needed with the installed Balsa 4.0.

## Behavior

The top procedure is `updown10`. Its input `in_sigs` is the record
`{data, mode, dir}`. Its output `count` carries a 4-bit value.

- `load`: replace the counter with `data`, regardless of direction.
- `count, up`: increment, wrapping from 9 to 0.
- `count, down`: decrement, wrapping from 0 to 9.

The updated value is output on every transaction. Send a load command first:
the manual does not explicitly initialize `count_reg`. Use load values 0-9
for decade-counter behavior; the 4-bit input type also permits values 10-15,
which the original example does not reject.

The manual's sample command stream is reproduced by `counter_test.balsa`.
Expected outputs are:

```text
8, 9, 0, 1, 0, 9, 8, 1, 0, 9
```

The manual mistakenly annotates the seventh command as another count to 9;
it actually decrements 9 to 8. The source listing itself is unchanged.

## Open and build

With Balsa on `PATH`, run from the repository root:

```sh
cd examples/tutorial/count10b
balsa-mgr .
```

Select `count10b`, then compile `count10b.breeze` in the Makefile pane.
The procedure name displayed underneath is `updown10`. Its graph is
`count10b.ps`; the View action uses your configured external viewer.

Equivalent command-line steps:

```sh
balsa-make-makefile -b -p .
make
make ps cost
./test.sh
```

Compilation, graph generation, cost estimation, and all ten simulated
transactions passed. `counter_test.balsa` and `test.sh` are original validation
code, not listings from the manual. The harness avoids the simulator's known
string-printing crash, checks values internally, and calls
`BalsaSimulationStop` only when every check passed. The shell script checks
that success marker; a simulator exit code of zero alone is insufficient.

The circuit and its original test harness are included as source; regenerate
compiled output, netlists, and diagrams locally.
