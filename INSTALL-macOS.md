# Installing Balsa 4.0 on Apple Silicon macOS

This guide supplements `INSTALL`. The compatibility changes are included on
this branch; [CODE-CHANGES-macOS.md](CODE-CHANGES-macOS.md) explains them.
A Git clone already contains the source and `configure`, so the original
instructions to download and unpack a tarball can be skipped.

## Dependencies

| Dependency | Tested version | Purpose |
| --- | --- | --- |
| Apple Clang | 21.0.0 | C/C++ compiler, invoked as `gcc` and `g++` |
| GLib | 2.86.2 | Core support library |
| GTK 2 | 2.24.33 | GUI and embedded editor |
| GMP | 6.3.0 | Multiprecision arithmetic |
| Guile | 3.0.11 | Scheme tools |
| `pkg-config` and `make` | Available in the test environment | Dependency discovery and build |
| Graphviz (`dot`) | Available in the test environment | Optional circuit diagrams |
| Ghostscript (`ps2pdf`) | 10.00 | Optional PDF graph conversion |

GTK 3 or GTK 4 alone does not satisfy GTK 2. GLib, GTK 2, GMP, `pkg-config`,
and `make` were already installed in the tested environment; this guide does
not establish a complete fresh-machine installation recipe for GTK 2.

If Xcode reports an unaccepted license, review and accept it in Terminal:

```sh
sudo xcodebuild -license
```

Install Guile if missing:

```sh
brew install guile
guile --version
```

Verify the required libraries:

```sh
pkg-config --modversion glib-2.0 gtk+-2.0 gmp
```

The additional `GUILE_LOAD_PATH`, `GUILE_LOAD_COMPILED_PATH`, and
`GUILE_SYSTEM_EXTENSIONS_PATH` exports suggested by Homebrew were not needed.
Leave them unset initially. Leave `BALSAHOME` and `BALSAPATH` unset for a normal
installation; they override the configured installation and search paths.

## Build and install

From this repository's root, with Homebrew under `/opt/homebrew`:

```sh
./configure --prefix="$HOME/.local/balsa" \
  --with-gmp-include=/opt/homebrew/include \
  --with-gmp-lib=/opt/homebrew/lib
make && make install
```

Use your actual Homebrew include and library directories if they differ.
This installs into your home directory without `sudo make install`. No
Autotools regeneration was needed for this checkout. After changing only
source files, rerun `make && make install`.

Add the installed tools to the current terminal's path:

```sh
export PATH="$HOME/.local/balsa/bin:$PATH"
command -v balsa-config
command -v balsa-c
```

Add the export once to `~/.zshrc` to use it in future zsh terminals.
Warnings about deprecated GLib/GTK APIs and legacy C++ strings remain in the
successful build. First-run Guile cache compilation may also print warnings;
check exit status and generated output rather than treating all stderr as
failure. `GUILE_AUTO_COMPILE=0` disables automatic cache compilation if desired.

## Graph viewing on macOS

Graphviz's `dot` generates the graph. From an example project with a generated
Makefile, run `make ps`. Balsa's upstream viewer default is `gv`, an external
X11 application. It is not embedded in the manager.

The optional macOS helper uses Ghostscript to convert PostScript to PDF and
macOS `open` to launch the default PDF viewer. It needs neither MacPorts nor
an X11 server. Use an existing Ghostscript installation, including one from
MacTeX, or install it if `ps2pdf` is missing:

```sh
command -v ps2pdf
# Only if missing:
brew install ghostscript
```

Homebrew's [Ghostscript package](https://formulae.brew.sh/formula/ghostscript)
provides both `gs` and `ps2pdf`.

Install the helper separately from the repository root; normal `make install`
does not install it:

```sh
install -m 755 extra/macos/balsa-view-ps "$HOME/.local/balsa/bin/balsa-view-ps"
command -v balsa-view-ps
```

In **Project > Environment Options**, set **PostScript viewer** to the full
path printed by that command. Save the setting. Alternatively, close the
manager and set `PSViewer=` in `~/.balsa-mgr` to that full path before
restarting. Do not put the literal `$HOME` variable in that setting.

The helper replaces the sibling generated `.pdf` each time a graph is viewed,
and propagates conversion errors. It leaves the upstream viewer default
unchanged. Viewer preferences and the installed helper remain local to your
machine; only the helper source and these instructions belong in Git.

For `gv` instead, the [MacPorts package](https://ports.macports.org/port/gv/)
provides installation instructions. Configure Balsa with the full path to
that executable. The PDF helper is an alternative, not a requirement.

## Examples and verification

See [examples](examples/README.md) for portable source projects and tests.
With installed tools on `PATH`, start from the repository root:

```sh
cd examples/tutorial/buffer1a
balsa-make-makefile -b -p .
make
make ps cost
balsa-mgr .
```

Counter, SSEM, and original program-counter projects provide `./test.sh`.
The original program-counter tests include 10 basic and 1,280 expanded
transactions. The manual counter checks 10 transactions, and the SSEM test
checks 12 memory transactions and halt. Graph generation and cost estimation
have passed for all four examples. The user also confirmed source display
and compilation through the GUI during setup; GUI actions are not automated
by these test scripts.

Verilog generation passed for the original program counter and manual counter
using the installed `example/four_b_rb` technology. From either project:

```sh
balsa-netlist -X example/four_b_rb -n verilog filename.breeze
```

Replace `filename.breeze` with that project's compiled file. Generated Verilog
is a structural netlist requiring the technology's gate definitions. Verilog
simulation and physical implementation have not been validated.

The simulator still has a known 64-bit crash in string-printing builtins
(`StringAppend` / `FormatDataGetBalsaObject`). The included simulation harnesses
avoid those builtins and check values internally; this is not a claim that
the simulator is fully compatible with all programs.

Espresso, real technology libraries, and separate Verilog simulation wrappers
are optional workflow-specific additions described in the original `INSTALL`.
They were not installed as part of these compatibility fixes.
