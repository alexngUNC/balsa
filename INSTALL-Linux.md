# Installing Balsa 4.0 on Linux

Use the same compatibility branch as on macOS. The Quartz editor settings
are only used on macOS, and the macOS PDF helper is optional.

On Ubuntu 24.04, install the build dependencies:

```sh
sudo apt update
sudo apt install build-essential pkg-config libgtk2.0-dev libgmp-dev guile-3.0 graphviz
```

Other distributions need equivalent packages. The current build checks for
GTK 2 at configure time, even if you only plan to use command-line tools.
Graphviz is only needed for circuit diagrams.

From a fresh checkout, build and install into your home directory:

```sh
CFLAGS="-O2 -g -std=gnu17" ./configure --prefix="$HOME/.local/balsa"
make -j"$(nproc)"
make install
export PATH="$HOME/.local/balsa/bin:$PATH"
```

Balsa still has old-style C function definitions. Selecting GNU C17 avoids
the newer C23 default on GCC 15 and later. Run `configure` on Linux instead
of copying configured Scheme files or binaries from another machine.

Verify compilation, simulation, and graph generation from the repository root:

```sh
(cd examples/program-counter && ./test.sh && breeze2ps program_counter)
```

Run `balsa-mgr` in a graphical session to use the manager. Its View button
uses an external PostScript viewer (`gv` by default); configure an installed
viewer in **Project > Environment Options**. The automated Linux check does
not exercise the GUI. The known simulator string-printing crash described in
[the compatibility notes](INSTALL-macOS.md#examples-and-verification)
is outside the simulation tests.
