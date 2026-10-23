# Building Balsa 4.0 on Apple Silicon macOS

These notes supplement `INSTALL` and describe dependencies, installation, and
verification for this checkout on October 23, 2026. Source edits are documented
separately in [CODE-CHANGES-macOS.md](CODE-CHANGES-macOS.md).

## 1. Use the existing Git checkout

Cloning this repository provides the source files that extracting the Balsa
tarball would provide. Skip downloading and extracting `balsa-4.0.tar.gz`.
The checkout includes `configure`; no Autotools regeneration was needed.

Run the build commands below from the repository root (the `balsa` directory).

## 2. Prepare the compiler and dependencies

If the compiler or Homebrew reports that the Xcode license has not been accepted,
review and accept it in Terminal:

```sh
sudo xcodebuild -license
```

Install Guile through Homebrew:

```sh
brew install guile
guile --version
```

The following versions were present on this machine:

| Dependency | Version | Purpose |
| --- | --- | --- |
| Apple Clang | 21.0.0 | C/C++ compiler; invoked through `gcc` and `g++` |
| GLib | 2.86.2 | Core support library |
| GTK 2 | 2.24.33 | Graphical tools and bundled editor |
| GMP | 6.3.0 | Multiprecision arithmetic |
| Guile | 3.0.11 | Scheme-based tools |

GLib, GTK 2, GMP, `pkg-config`, and `make` were already available; installing
them was not part of this session. A fresh machine needs these prerequisites
as well. GTK 3 or GTK 4 alone does not satisfy this checkout's GTK 2 requirement.

Check library discovery with:

```sh
pkg-config --modversion glib-2.0 gtk+-2.0 gmp
```

The additional `GUILE_LOAD_PATH`, `GUILE_LOAD_COMPILED_PATH`, and
`GUILE_SYSTEM_EXTENSIONS_PATH` exports suggested by Homebrew were not needed
for the build and installation. Leave them unset initially.

## 3. Apply the compatibility changes

Before building an unpatched checkout, apply the source fixes described in
[CODE-CHANGES-macOS.md](CODE-CHANGES-macOS.md). They cover modern compiler
requirements, 64-bit GTK types, macOS fonts and rendering, output-pane clicks,
and Guile 3 graph generation. They are already applied in this working tree.

## 4. Configure, build, and install

With Homebrew under `/opt/homebrew`, run:

```sh
./configure --prefix="$HOME/.local/balsa" \
  --with-gmp-include=/opt/homebrew/include \
  --with-gmp-lib=/opt/homebrew/lib
make && make install
```

This installs into your home directory and does not require `sudo make install`.
If configuration has already succeeded and you are only applying the source
fixes above, rerun `make && make install` directly.

Warnings about deprecated GLib/GTK APIs and old C++ string usage remained during
the successful build. The errors addressed above were the build blockers.

## 5. Add Balsa to your PATH

For the current terminal:

```sh
export PATH="$HOME/.local/balsa/bin:$PATH"
```

Add that same line once to `~/.zshrc` for future zsh terminals. Do not set
`BALSAHOME` or `BALSAPATH` for the normal installation; the original README
advises leaving them unset unless overriding the installation location.

## 6. Check the installation and start using it

```sh
command -v balsa-config
command -v balsa-c
```

Both paths should be under `$HOME/.local/balsa/bin`.

Launch the project manager:

```sh
balsa-mgr
```

Or compile an existing source file from its directory:

```sh
balsa-c filename.balsa
```

Compilation produces a `.breeze` circuit file. Replace `filename.balsa` with
your actual input file.

## 7. Graph generation and viewing

Graphviz (`dot`) is needed to generate the handshake circuit diagram. It was
already available on this machine. Verify it with `command -v dot`.

From a tutorial project directory containing a generated Makefile:

```sh
make ps
```

The GUI defaults to `gv` for viewing PostScript, but `gv` is not installed on
this machine. Ghostscript's `ps2pdf` was available instead. For the first
buffer tutorial, use:

```sh
ps2pdf buffer1a.ps buffer1a.pdf
open buffer1a.pdf
```

This does not change the GUI's configured PostScript viewer. Its View button
will still try `gv` until that viewer setting is changed.

Guile may print cache-compilation notes and warnings about possibly unbound
variables during the first run of a Scheme tool. Those messages alone do not
indicate failure; check the command's exit status and generated output.
`GUILE_AUTO_COMPILE=0` disables automatic cache compilation if desired.

## Optional synthesis and simulation components

The original `INSTALL` also describes Espresso for synthesis, technology
packages, and a separate package for Verilog simulation. These were not added
as part of this core installation. Simulation requires a test fixture.

## Validation status

The full build and installation passed. The `buffer1a` tutorial passed
project-based Makefile generation, compilation, cost estimation, and
PostScript graph generation with Guile 3. The generated PDF was inspected and
matches the expected single-place buffer structure. The user confirmed correct
source display and successful compilation through Balsa Manager.

Simulation and Verilog backend operation have not yet been validated.
