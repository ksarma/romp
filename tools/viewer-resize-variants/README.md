# viewer-resize bench variants

Inputs for `tools/viewer-resize-bench.mjs --pane-js FILE` and `--pane-css FILE`: each file is inlined into the pane page
after the viewer bundle and the harness, before the viewer opens. They isolate one term of a drag frame's cost:

- `stub-bodyw.js`: drops the width observer's `--fv-body-w` write on the body (file-view.ts, the width observer), so a
  run measures the style recalculation that write costs.
- `stub-widthro.js`: makes the first ResizeObserver constructed in the pane inert (the width observer, created before the
  actions mount), so no viewer repaint runs on a width change; the panel's own observers and window resize still run.
- `stub-allro.js`: the first three observers inert (width observer, the panel's sizer, its card sizer).
- `stub-widthro-bodyw.js`: both stubs, the floor: the browser's own relayout of the document per width step.
- `css-fence-block.css`: fence rows as blocks with no counter, against the per-line flex rows.
- `css-table-plain.css`: tables as plain `display: table` with no cap or translate.
- `css-cv.css`: `content-visibility: auto` on the top-level blocks of the rendered markdown.

The stubs count what they did: `window.__bodywDropped`, `window.__roInert`, `window.__roMade`; a run's `paints_total`
stays at the mount's count when the width observer is inert.
