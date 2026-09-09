// stub: the FIRST ResizeObserver constructed in the pane (file-view.ts's width observer, created before the actions mount) is inert
(function () { var RO = window.ResizeObserver, n = 0, INERT = 1; window.__roInert = 0; window.__roMade = 0;
  window.ResizeObserver = function (cb) { var k = n++; window.__roMade = n; var ro = new RO(cb);
    if (k < INERT) { window.__roInert++; return { observe: function () {}, unobserve: function () {}, disconnect: function () {} }; } return ro; };
  window.ResizeObserver.prototype = RO.prototype; })();
// stub: the width observer's --fv-body-w write on the body is dropped (every other setProperty passes through)
(function () { var sp = CSSStyleDeclaration.prototype.setProperty; window.__bodywDropped = 0;
  CSSStyleDeclaration.prototype.setProperty = function (n, v, p) { if (n === "--fv-body-w") { window.__bodywDropped++; return; } return sp.call(this, n, v, p); }; })();
