---
title: The file viewer gets a text-size control (A− / A+ and a percentage reset, Ctrl/Cmd + wheel; nine steps from 70% to 200%, kept per browser) and a fluid rendered-markdown layout: the prose measure follows the pane up to a cap that scales with the text size, a table takes the pane width and scrolls in its own box beyond it, and every reflow (a size step, the body resized) re-runs the comments panel paint pass through the seam
status: candidate
where: fork branch `mdzoom` (ui/webview/file-view.ts TEXT_SIZES, stepTextSize, foldWheel, the A− / A+ / reset buttons, the wheel handler and the body ResizeObserver; ui/webview/styles.css and feed.css the "text size and measure" block and the .fileview-md rules; docs/guide.md Files, docs/reference.md; ui/webview/file-view-text-size.test.ts)
added: 2026-09-07
pr:
tier: feature
offered:
closed:
---
Two asks from one walk of the file viewer: the rendered markdown could not be zoomed, and a table did not follow the Files pane when the pane was resized. The size is one CSS custom property on the viewer root (`--fv-scale`, from a `data-fv-text` step the sheets map), read by the prose, its headings, inline and fenced code, and the Raw view's rows and gutter, so they scale together; the title bar, the aside, a figure's region chip and the editor keep the page's size. Persisted like the Rendered/Raw choice, per browser in localStorage, with any foreign value reading as 100. The measure moved from the `.fileview-md` root to its prose blocks and scales with the size, so a table or a code block takes the pane's width when it needs it and a wider table scrolls in its own box with whole words kept (`overflow-wrap: normal` against the root's `anywhere`); the page never widens. Both reflows fire the seam's onRendered, so the comments panel re-runs its paint pass over the moved text; a ResizeObserver on the body is the width event, never a timer. Upstream ships the same viewer and sheets, so this ports as one change.
