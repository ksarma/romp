// stub: the viewer's width observer (file-view.ts watchBodyWidth's observer of the body, picked by its callback) is inert, so no
// viewer repaint runs on a width change; every other observer, the tables' and the figures' among them, and window resize still run
(function () { var RO = window.ResizeObserver, INERT = ["width"]; window.__roInert = 0; window.__roMade = 0; window.__roKinds = [];
  var kind = function (cb) { var s = String(cb);   // the pane's observers told apart by their callbacks, never by the order they are made in
    if (/hideFloatOnScroll/.test(s)) return "sizer";                                    // file-comments.ts: the panel's sizer
    if (/^\(\)\s*=>\s*this\.scheduleLayout\(\)$/.test(s.trim())) return "cards";         // file-comments.ts: its card sizer
    if (/--fv-table-w/.test(s)) return "tables";                                         // file-view.ts watchBodyWidth: the tables' observer
    if (/\.clientWidth\b/.test(s) && /contentRect\.width/.test(s)) return "width";       // file-view.ts watchBodyWidth: the body's width observer
    if (/contentRect\.height === 0/.test(s)) return "figures";                           // file-view.ts watchFigureBoxes: the figures' observer
    return "other"; };
  window.ResizeObserver = function (cb) { var k = kind(cb); window.__roMade++; window.__roKinds.push(k);
    if (INERT.indexOf(k) >= 0) { window.__roInert++; return { observe: function () {}, unobserve: function () {}, disconnect: function () {} }; } return new RO(cb); };
  window.ResizeObserver.prototype = RO.prototype; })();
// stub: the width watch's --fv-body-w writes, on each top-level table, are dropped (every other setProperty passes through)
(function () { var sp = CSSStyleDeclaration.prototype.setProperty; window.__bodywDropped = 0;
  CSSStyleDeclaration.prototype.setProperty = function (n, v, p) { if (n === "--fv-body-w") { window.__bodywDropped++; return; } return sp.call(this, n, v, p); }; })();
