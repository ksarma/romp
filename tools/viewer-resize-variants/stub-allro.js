// stub: the first THREE ResizeObservers (the width observer, the panel sizer, the card sizer) are inert
(function () { var RO = window.ResizeObserver, n = 0, INERT = 3; window.__roInert = 0; window.__roMade = 0;
  window.ResizeObserver = function (cb) { var k = n++; window.__roMade = n; var ro = new RO(cb);
    if (k < INERT) { window.__roInert++; return { observe: function () {}, unobserve: function () {}, disconnect: function () {} }; } return ro; };
  window.ResizeObserver.prototype = RO.prototype; })();
