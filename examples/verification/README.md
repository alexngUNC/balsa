# Bundled-data and dual-rail verification

The same counter and dot-product arithmetic tests have separate entry points:

```text
verification/
  bundled-data/
    count10b/test.sh
    dot-product/test.sh
  dual-rail/
    count10b/test.sh
    dot-product/test.sh
```

Circuit sources remain in `tutorial/count10b` and `dot-product`; they are not
duplicated or changed to select an encoding. The shared `run.py` compiles Breeze
and maps the same circuit with either `example/four_b_rb` (bundled data) or
`example/dual_b` (dual rail), using the technology's default style options.

With Balsa tools and Xcelium configured:

```sh
module load xcelium/25.03.003
examples/verification/bundled-data/count10b/test.sh
examples/verification/bundled-data/dot-product/test.sh
examples/verification/dual-rail/count10b/test.sh
examples/verification/dual-rail/dot-product/test.sh
```

The commands above run from the repository root. Each invocation prints its
external artifact location. Set `VERIFY_OUTPUT_ROOT` to retain all runs under
one directory; encoding/circuit subfolders are appended automatically. By
default a new temporary root is used. `XRUN` can select the Xcelium executable.
Source changes need no separate toolkit rebuild; each invocation recompiles
the circuit. All generated netlists, protocol adapters, logs, and evidence are
external to the checkout.

## Identical functional tests

| Circuit | Positive scenarios, per encoding | Negative scenarios |
| --- | --- | --- |
| count10b | Original 10 vectors with nominal/delayed responses; 1,181 expanded vectors with nominal/delayed responses | Wrong expectation; withheld output acknowledgement |
| dot product | Same 816 host-oracle vectors with nominal/delayed responses | Wrong expectation; withheld output acknowledgement |

The counter bench independently checks its expectations with modular
arithmetic. The dot-product bench independently checks Python expectations with
native integer multiplication. The underlying Breeze self-checks run before
mapping and require `BalsaSimulationStop called`. The counter's Breeze test is
the original ten-vector harness; its expanded suite is an HDL verification
stage. The dot product uses the same 816 vectors in both simulators.

## Dual-rail protocol adapter

The generated DUT is a real dual-rail structural circuit. A generated
test-only adapter lets the same functional scoreboard drive it:

- A pull input has a request and two acknowledgement/data rails per bit. The
  adapter sends `10` for zero and `01` for one (rail0, rail1), and `00` as spacer.
- A push output has two request/data rails per bit and one acknowledgement.
  The adapter asserts the scoreboard's request only after every bit has a valid
  code, and keeps it asserted until **every** bit returns to spacer.
- It decodes rail1 into a held scoreboard value. It does not provide a
  behavioral replacement for the DUT arithmetic or internal handshake cells.
- During active operation it rejects unknown rails, illegal `11` codes, and
  withdrawal/change of a completed word before acknowledgement. Partial word
  arrival and partial return-to-zero do not count as complete transfers.

The dot product's generated `initialise` input is forwarded to the bench's
initialization pulse. Required `balsa_simulate` and `balsa_init_time` settings
are enabled for both encodings. The top-level dual-rail module is renamed only
to bind the adapter; its internal structural logic and gate models are unchanged.
Existing bench timeouts and four-phase checks remain enabled.

This is a zero-extra-delay test adapter. The delayed scenarios vary supplier,
consumer, and return-to-zero response timing; they do not independently skew
every rail or prove physical delay insensitivity. Invalid-rail injection is
not part of the current fault-injection suite.

## Observed result

On RHEL 8.10, Xcelium 25.03-s003 successfully simulated the dual-rail counter
and dot product with all listed scenarios on 2026-11-15. The counter reached
200/200 load and 320/320 count bins in both expanded runs. The dot product
reached 256/256 lane/bit-pair and 144/144 boundary bins in both positive runs.

Each output directory contains `evidence.json`, mapping/compilation/Breeze logs,
and `runs/<scenario>/console.log` with an exit status. Positive acceptance
requires successful runtime exit, all CHECK records, the scenario's PASS marker,
and required coverage. Negative acceptance requires its specific intended fatal
message; license failures and arbitrary errors do not qualify.

These results establish finite functional simulation coverage for these two
circuits and the tested default technology styles. They do not establish every
Balsa dual-rail option, formal equivalence, physical timing, or GUI behavior.
