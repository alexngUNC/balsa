# Balsa examples

Use the installed `balsa-c`, `balsa-make-makefile`, `breeze2ps`, and `breeze-sim`
from `PATH`. Graph generation requires Graphviz (`dot`). See
[macOS installation](../INSTALL-macOS.md) for setup and viewer choices.

| Project | Origin | Top procedure | Simulation checks |
| --- | --- | --- | --- |
| [First buffer](tutorial/buffer1a/) | Manual, section 2.1, printed page 9 | `buffer1` | Compile and graph generation |
| [Loadable counter](tutorial/count10b/) | Manual, section 3.6, printed pages 43-44 | `updown10` | 10 transactions |
| [SSEM processor](tutorial/ssem/) | Manual, section 6.6, printed pages 73-75 | `SSEM` | 12 memory transactions and halt |
| [Program counter](program-counter/) | Original standalone design inspired by the manual | `program_counter` | 10 basic and 1,280 expanded transactions |

The tutorial circuits are transcribed from *Balsa: A Tutorial Guide*, version
3.5 (University of Manchester, printed May 19, 2006). The counter and SSEM
retain the listed circuit logic, with formatting and comment changes. The
buffer retains the listed behavior with shortened comments. Test harnesses
and runners are original additions; they are not listings from the manual.
The manual PDF is not bundled. Each project guide documents its provenance
and known limitations.

From a project directory:

```sh
balsa-mgr .
```

Or generate and build the project Makefile:

```sh
balsa-make-makefile -b -p .
make
make ps cost
# Counter, SSEM, and program-counter projects also provide:
./test.sh
```

Simulation tests check the compiled handshake circuits. They require the
`BalsaSimulationStop called` success marker, not just simulator exit status.
They avoid a known unresolved 64-bit simulator crash in string-printing
builtins. These checks do not establish physical timing correctness or
constitute formal verification.

Build outputs are deliberately not versioned: regenerate Makefiles, Breeze
files, diagrams, PDFs, Verilog, and cell maps on your machine. The examples
are standalone projects and are not added to the toolkit's default build.
