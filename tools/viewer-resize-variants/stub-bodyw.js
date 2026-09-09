// stub: the width observer's --fv-body-w write on the body is dropped (every other setProperty passes through)
(function () { var sp = CSSStyleDeclaration.prototype.setProperty; window.__bodywDropped = 0;
  CSSStyleDeclaration.prototype.setProperty = function (n, v, p) { if (n === "--fv-body-w") { window.__bodywDropped++; return; } return sp.call(this, n, v, p); }; })();
