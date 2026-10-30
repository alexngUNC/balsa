# Required source changes for Balsa on macOS

These notes record the compatibility fixes applied to Balsa 4.0, based on commit
`4fd341e`, during setup on Apple Silicon macOS on October 23, 2026. The fixes
are already applied in this working tree. For dependencies, installation,
and verification commands, see [INSTALL-macOS.md](INSTALL-macOS.md).

## Compatibility changes

These fixes address errors reported by the modern compiler without disabling
its diagnostics. File paths below are relative to the repository root.

### Explicit conversion in the bundled Scintilla editor

In `extra/scintilla-wrapper/ScintillaGTK.cxx`, inside
`ScintillaGTK::AddToPopUp`, change the `cmd` entry of the
`GtkItemFactoryEntry` initializer:

```diff
     menuSig,
-    cmd,
+    static_cast<guint>(cmd),
```

The callback action field is unsigned. The explicit conversion resolves
`non-constant-expression cannot be narrowed from type 'int' to 'guint'`.
This build uses the file directly under `extra/scintilla-wrapper`, rather than
the other copy under `extra/scintilla-wrapper/scintilla/gtk`.

### Declare the simulator's HLA component functions

In `src/breeze-sim/components_4phase.h`, immediately after the existing
`BrzHLA_active_sync` declaration, add:

```c
void BrzHLA_active_push (int num, char *args[]);
void BrzHLA_passive_sync (int num, char *args[]);
void BrzHLA_passive_push (int num, char *args[]);
```

These functions already have definitions in `components_4phase_hla.c`, but
their declarations were missing from the header used by `simulate.c`.
Modern C rejects the implicit function declarations.

### Declare the simulator's post-initialization registration function

In `src/breeze-sim/simulate.h`, immediately after the existing
`InitialiseBreezeComponents` declaration, add:

```c
extern void AddComponentPostInitialisation (_FCT2 fct, struct comp *comp, int optional_data);
```

The definition already exists in `simulate.c`. This declaration makes it
available to the component implementation that calls it.

### Preserve the editor's GTK type ID on 64-bit systems

Opening a project file initially crashed in `g_type_fundamental`, called while
creating the Scintilla editor. The bundled editor stored and returned a GTK
type ID as `guint` (32 bits), truncating the 64-bit `GType` on this Mac.

In `extra/scintilla-wrapper/ScintillaGTK.cxx`, use:

```c++
GType scintilla_get_type() {
    static GType scintilla_type = 0;
```

Keep the rest of that function unchanged. Also change its declaration in
`extra/scintilla-wrapper/scintilla/include/ScintillaWidget.h` to:

```c
GType scintilla_get_type (void);
```

Rebuild and reinstall after changing both files. The full build passed, and a
non-GUI check confirmed that the complete type ID resolves to `Scintilla` and
is a subtype of `GtkContainer`. The user subsequently confirmed that opening the tutorial source in the GUI
worked after the additional font and painting fixes below.

### Use a Pango font on macOS Quartz

After fixing the type ID, loading a file exposed a second crash in
`SurfaceImpl::Descent(Font&)`. The legacy `helvetica` GDK font was unavailable,
leaving a null `GdkFont` that the metrics code dereferenced.

In `extra/scintilla-wrapper/PlatGTK.cxx`, in `Platform::DefaultFont()`, replace
the final `return "helvetica";` with:

```c++
#ifdef GDK_WINDOWING_QUARTZ
    // Quartz needs Pango fonts; the legacy GdkFont may be unavailable.
    return "!monospace";
#else
    return "helvetica";
#endif
```

The `!` prefix selects this version of Scintilla's Pango font implementation.
The change preserves the existing default on other GTK backends. The full
build and a non-GUI check of default-font selection, creation, and release
passed. The user subsequently confirmed the tutorial source opened in the GUI
after the additional rendering fixes below.

### Use the GTK 2 text-buffer API for output-pane clicks

Clicking the execution output pane crashed in `gtk_editable_get_position`,
with `invalid cast from 'GtkTextView' to 'GtkEditable'`. In
`src/balsa-mgr/executionmanager.c`, `OnTextBox_ButtonPressed` still used the
GTK 1 editable API even though the output panes had become GTK 2 text views.

The handler now obtains the `GtkTextBuffer` from the `GtkTextView`, translates
the click coordinates into a text iterator, reads the clicked line, and uses
`gtk_text_buffer_select_range` for selection. It validates diagnostic
`filename:row:column` fields before opening a source location and frees the
temporary text and filename. Right-click menu behavior is retained.

The full build passed after this change. The supplied buffer library also compiled directly with `balsa-c`,
producing a Breeze file in a temporary output directory. This confirms
that the source file itself parses successfully. The user subsequently
confirmed compilation through the GUI for the new `buffer1a` project. Clicking
an actual diagnostic to navigate to its source location remains unverified.

### Remove the empty Scheme expression in circuit graph generation

Guile 3 rejected `breeze2ps.scm` with `sequence of zero expressions in form
(begin)`. In `share/scheme/breeze2ps.scm`, replace:

```scheme
(if (string=? breeze-tech "common")
    (begin)
    (brz-get-technology))
```

with:

```scheme
(if (not (string=? breeze-tech "common"))
    (brz-get-technology))
```

This keeps the same conditional technology loading without an empty expression.
After reinstalling, the `buffer1a` project's Makefile generation, compilation,
cost estimation, and PostScript graph generation all passed using Guile 3.
The rebuilt tools, including the output-pane click fix, were installed into
`$HOME/.local/balsa` during this tutorial setup.

### Fill the final character width when using modern Pango

With Pango fonts enabled, text could be clipped, overlap, or appear garbled.
The `SurfaceImpl::MeasureWidths` loops in
`extra/scintilla-wrapper/PlatGTK.cxx` expected an extra end-of-line cluster
from Pango. Modern Pango stops without that sentinel, leaving the last
character's position uninitialized (including the only character of a
one-character run).

After each cluster loop, the implementation now gets the complete layout's
pixel width with `pango_layout_get_pixel_size` and fills all remaining source
positions. This covers UTF-8, DBCS, and the single-byte fallback. Converted
UTF-8 strings are also passed to Pango with their converted byte length,
rather than the source byte length.

The full build passed. A regression check using the actual UTF-8 and
single-byte width-calculation source passed 12 cases, including one-character
runs, Balsa statements, and multibyte UTF-8 text. This fixed character spacing,
but a separate repeated-line artifact required the painting change below.

### Bypass the shared line pixmap on macOS

After the width fix, clicking a source line could repeat that line in other
rows while hiding other lines. The source file on disk remained unchanged.
To bypass the suspected stale line-pixmap copies on Quartz,
`initialise_editor` in `src/balsa-mgr/editor.c` now starts with:

```c
#ifdef GDK_WINDOWING_QUARTZ
    /* Avoid stale copies of the shared line pixmap on the Quartz backend. */
    SendEditor (SCI_SETBUFFEREDDRAW, 0, 0);
#endif
```

This selects Scintilla's direct painting path for macOS. Other GTK backends
retain buffered drawing. The full build passed, and the user confirmed the
source displayed correctly after restarting. Exhaustive scrolling and resizing
checks have not been performed.

## Optional macOS graph-viewer helper

`extra/macos/balsa-view-ps` is a standalone shell helper for the manager's
configurable PostScript viewer command. It converts the selected graph using
Ghostscript's `ps2pdf` and opens the sibling PDF with macOS `open`. It checks
for missing inputs and dependencies, supports filenames containing spaces,
and propagates conversion errors.

This is an optional macOS integration utility, not a compiler or rendering fix.
It does not change Balsa's upstream `gv` default. Its Ghostscript dependency,
separate installation step, and local viewer setting are described in
[INSTALL-macOS.md](INSTALL-macOS.md). Do not commit personal `~/.balsa-mgr`
settings. The helper can be included in the fork with these setup notes.

## What to commit

Commit the compatibility source edits and these two macOS guides. Review the
file list explicitly before staging: this checkout has many generated files.

`share/scheme/base.scm` and `share/scheme/globals.scm` were regenerated by
`configure` from their `.in` templates and now contain this machine's absolute
installation paths. Those path substitutions are build output, not portability
fixes; keep them out of the compatibility commit. Likewise, exclude object
files, executables, generated Makefiles, caches, and local configuration logs.

Curated tutorial projects and the original program-counter design are included
in [examples](examples/README.md). Commit their sources, project definitions,
test runners, and guides, not generated netlists or diagrams. Personal working
projects and installed copies remain outside the repository.
