// stub: the width watch's --fv-body-w writes, on each top-level table, are dropped (every other setProperty passes through)
(function () { var sp = CSSStyleDeclaration.prototype.setProperty; window.__bodywDropped = 0;
  CSSStyleDeclaration.prototype.setProperty = function (n, v, p) { if (n === "--fv-body-w") { window.__bodywDropped++; return; } return sp.call(this, n, v, p); }; })();
