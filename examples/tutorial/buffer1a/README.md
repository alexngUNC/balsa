# Buffer1a tutorial project

This project follows section 2.1 (printed page 9) and section 2.5 (printed pages
13-17) of the Balsa 3.5 manual. It uses the installed Balsa 4.0 tools.

## Open the prepared project

With installed Balsa tools on `PATH`, run from the repository root:

```sh
cd examples/tutorial/buffer1a
balsa-mgr .
```

Alternatively, use Project > Open in Balsa Manager and choose this project
directory. A project is represented by the file named `Project` inside it.
The source file has already been added to the project; there is no need to
create another project over it.

Select `buffer1a` in the Files pane to open the source. Its procedure is named
`buffer1`, as in the manual. In the Makefile tab, compile `buffer1a.breeze`.
An existing compiled file may make this action report that it is up to date.
The graph target is `buffer1a.ps`.

## Equivalent steps to create a project in the GUI

For a fresh project in another empty directory:

1. Choose Project > New.
2. Set a project name and choose the new project directory.
3. Set File Import Path to `.` and use the Breeze simulator.
4. Save the project.
5. Put `buffer1a.balsa` in that directory.
6. Choose Files > Add Files into Project and select `buffer1a.balsa`.
7. Save, then compile `buffer1a.breeze` from the Makefile tab.

## Code review

The source matches the manual's behavior: read one byte from `i` into `x`,
then send that byte through `o`, repeating forever. The semicolon between
the communications requires them to happen in sequence.

- `buffer1a` is the filename; `buffer1` is the procedure name. The difference
  is intentional and follows the manual.
- `byte` gives the input, output, and storage variable an 8-bit width.
- Keep the semicolon after `i -> x`, and do not add one after `o <- x`.
- Use plain ASCII `->` and `<-` when copying the code from the PDF.

The source compiles with the Balsa 4.0 compatibility branch.

## Command-line checks

From this directory:

```sh
balsa-make-makefile -b -p .
make buffer1a.breeze
make cost
make ps
```

These checks passed:

- Project-based Makefile generation through Guile 3.
- Compilation to `buffer1a.breeze`, containing procedure `buffer1` with 8-bit
  input `i` and output `o`.
- Cost estimation, reporting `buffer1 = 268.25` in the tool's model.
- Handshake circuit graph generation to `buffer1a.ps` through Graphviz.

Regenerate the Makefile, Breeze file, and PostScript graph locally.
Simulation needs a test fixture and is the next tutorial stage; this project
does not yet include a test fixture. Source display and compilation through the GUI were manually checked during
setup. The shell commands do not automate GUI verification.

## Compatibility fixes installed

The source fixes are documented in
[CODE-CHANGES-macOS.md](../../../CODE-CHANGES-macOS.md). Dependencies and
installation are documented in [INSTALL-macOS.md](../../../INSTALL-macOS.md). In particular,
the latest installation includes the GTK type-ID and font fixes, the
`GtkTextView` output-click fix, and a Guile 3 fix in `breeze2ps.scm`.

The graph fix replaces an `if` with an empty `(begin)` branch with an equivalent
conditional call to `brz-get-technology`. Guile 3 rejects the empty expression.
The example itself did not require a language change.
