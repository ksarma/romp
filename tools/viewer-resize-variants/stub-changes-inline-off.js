// stub: the shared settings store (settings.ts, key romp:settings) starts with Show changes inline OFF, so the Comments
// panel paints no change mark (file-comments.ts paintChanges returns before painting); the change cards still render
(function () { try { var K = "romp:settings", s = {}; try { s = JSON.parse(localStorage.getItem(K) || "{}") || {}; } catch (e) { s = {}; }
  s.changesInline = false; localStorage.setItem(K, JSON.stringify(s)); window.__inlineOff = 1; } catch (e) { window.__inlineOff = 0; } })();
