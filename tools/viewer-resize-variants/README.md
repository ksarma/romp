# viewer-resize bench variants

Inputs for `tools/viewer-resize-bench.mjs --pane-js FILE` and `--pane-css FILE`: each file is inlined into the pane page
after the viewer bundle and the harness, before the viewer opens. They isolate one term of a drag frame's cost:

- `stub-bodyw.js`: drops the width watch's `--fv-body-w` writes, which land on each top-level table (file-view.ts
  watchBodyWidth), so a run measures the style recalculation those writes cost.
- `stub-widthro.js`: makes the viewer's width observer inert (watchBodyWidth's observer of the body), so no viewer repaint
  runs on a width change; the panel's own observers, the viewer's tables' and figures' observers and window resize still run.
- `stub-allro.js`: the width observer and the panel's two sizers inert (file-comments.ts: the sizer and the card sizer); the
  viewer's tables' and figures' observers still run.
- `stub-widthro-bodyw.js`: both stubs, the floor: the browser's own relayout of the document per width step.
- `stub-changes-inline-off.js`: the shared settings store starts with Show changes inline off (settings.ts changesInline),
  so the panel paints comment highlights but no change marks; the change cards stay in the aside.
- `css-fence-block.css`: fence rows as blocks with no counter, against the per-line flex rows.
- `css-table-plain.css`: tables as plain `display: table` with no cap or shift (a top-level table's position and left undone).
- `css-cv.css`: `content-visibility: auto` on the top-level blocks of the rendered markdown.

The observer stubs pick each observer by its callback, never by the order the pane constructs them in: the viewer's
figures' observer (watchFigureBoxes) and its tables' observer came in after the stubs were first written and took the
first places, so a stub keyed on construction order made the wrong observers inert. The pane constructs five: the
figures' observer, the width observer, the tables' observer, the panel's sizer and its card sizer. `window.__roKinds`
lists the kinds a run constructed, in order. The tables' observer writes each top-level table's own width as
`--fv-table-w` (its offsetWidth) whenever the table's size changes, the width the table's shift into the gutters reads;
no stub makes it inert, and under `css-table-plain.css`, where the table has no shift, its write moves nothing but still
restyles the table, as the base variant's `--fv-body-w` write did. The figures' observer re-decides a figure's control at
the next animation frame after its box changes.

The stubs count what they did: `window.__bodywDropped`, `window.__roInert`, `window.__roMade`, `window.__roKinds`,
`window.__inlineOff`; a run's `paints_total` stays at the mount's count when the width observer is inert.
